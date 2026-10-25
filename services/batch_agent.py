"""
services.batch_agent – Batch download agent for ClipsFlow.

Accepts a list of URLs for one user/job and runs each one through the
existing ClipPipeline (and therefore only through the configured provider
adapters). It adds:

* a provider allowlist (URLs whose provider is not allowlisted are rejected
  up front, before any network call),
* an explicit blocklist for music-streaming hosts (Spotify, Apple Music,
  SoundCloud, ...). ClipsFlow never extracts or decrypts DRM-protected media,
* a per-job queue with per-item status,
* retries with exponential backoff for retryable provider errors,
* a global concurrency limit and a minimum interval between item starts,
* cancellation (`/batch cancel`).

The agent is transport-agnostic: it has no knowledge of Telegram. The bot
layer supplies a `process` coroutine (normally `pipeline.process`) and an
optional `on_update` callback used to report progress.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Optional

from core.models import ClipResult, ClipStatus
from core.source_routing import parse_domain, provider_candidates_for_url
from core.url_safety import normalize_url, redact_url
from providers.base import is_valid_url

logger = logging.getLogger(__name__)

# Hosts that are always rejected: these services deliver DRM-protected or
# license-restricted audio and ClipsFlow must never be used to extract it.
BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (
    "spotify.com",
    "spotify.link",
    "music.apple.com",
    "itunes.apple.com",
    "soundcloud.com",
    "on.soundcloud.com",
    "deezer.com",
    "tidal.com",
    "music.amazon.com",
    "music.youtube.com",
)


class ItemStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TERMINAL_ITEM_STATES = {ItemStatus.DONE, ItemStatus.FAILED, ItemStatus.REJECTED, ItemStatus.CANCELLED}


class BatchErrorCode(str, Enum):
    NOT_AUTHORIZED = "not_authorized"
    DISABLED = "batch_disabled"
    EMPTY = "empty_batch"
    TOO_MANY_URLS = "too_many_urls"
    JOB_ALREADY_ACTIVE = "job_already_active"
    NO_ACTIVE_JOB = "no_active_job"
    INVALID_URL = "invalid_url"
    BLOCKED_HOST = "blocked_host"
    PROVIDER_NOT_ALLOWED = "provider_not_allowed"
    PIPELINE_ERROR = "pipeline_error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class BatchError(Exception):
    """Structured error returned to callers (and rendered by the bot)."""

    code: BatchErrorCode
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict:
        return {"code": self.code.value, "message": self.message}


@dataclass
class BatchConfig:
    enabled: bool = True
    allowed_providers: tuple[str, ...] = ()
    max_urls: int = 50
    concurrency: int = 1
    min_interval_seconds: float = 2.0
    max_retries: int = 2
    retry_base_seconds: float = 2.0
    retry_max_seconds: float = 30.0

    @classmethod
    def from_settings(cls, settings) -> "BatchConfig":
        return cls(
            enabled=bool(getattr(settings, "batch_agent_enabled", False)),
            allowed_providers=tuple(getattr(settings, "batch_allowed_providers", ()) or ()),
            max_urls=int(getattr(settings, "batch_max_urls", 50)),
            concurrency=max(1, int(getattr(settings, "batch_concurrency", 1))),
            min_interval_seconds=float(getattr(settings, "batch_min_interval_seconds", 2.0)),
            max_retries=max(0, int(getattr(settings, "batch_max_retries", 2))),
            retry_base_seconds=float(getattr(settings, "batch_retry_base_seconds", 2.0)),
        )


@dataclass
class BatchItem:
    index: int
    url: str
    status: ItemStatus = ItemStatus.QUEUED
    attempts: int = 0
    provider: Optional[str] = None
    error: Optional[BatchError] = None
    result: Optional[ClipResult] = None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "url": redact_url(self.url),
            "status": self.status.value,
            "attempts": self.attempts,
            "provider": self.provider,
            "error": self.error.to_dict() if self.error else None,
        }


@dataclass
class BatchJob:
    job_id: str
    owner_id: int
    items: list[BatchItem]
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    task: Optional[asyncio.Task] = field(default=None, repr=False)

    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in ItemStatus}
        for item in self.items:
            out[item.status.value] += 1
        return out

    @property
    def is_active(self) -> bool:
        return self.status in {JobStatus.QUEUED, JobStatus.RUNNING}

    def summary(self) -> str:
        c = self.counts()
        parts = [f"{k}={v}" for k, v in c.items() if v]
        return f"Job {self.job_id} [{self.status.value}] {len(self.items)} items: " + ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "owner_id": self.owner_id,
            "status": self.status.value,
            "counts": self.counts(),
            "items": [i.to_dict() for i in self.items],
        }


def is_admin(user_id: Optional[int], admin_ids) -> bool:
    """Deny by default: an empty TELEGRAM_ADMIN_IDS means nobody is authorized."""
    if user_id is None or not admin_ids:
        return False
    return user_id in set(admin_ids)


def _host_blocked(domain: str) -> bool:
    return any(domain == s or domain.endswith("." + s) for s in BLOCKED_HOST_SUFFIXES)


def classify_batch_url(url: str, allowed_providers) -> tuple[str, Optional[str], Optional[BatchError]]:
    """Return (normalized_url, provider, error). Pure, no network."""
    normalized = normalize_url(url or "")
    if not normalized or not is_valid_url(normalized):
        return url, None, BatchError(BatchErrorCode.INVALID_URL, "Not a valid http(s) URL.")
    domain = parse_domain(normalized)
    if _host_blocked(domain):
        return normalized, None, BatchError(
            BatchErrorCode.BLOCKED_HOST,
            f"{domain} is a music-streaming/DRM service; ClipsFlow does not download from it.",
        )
    candidates = provider_candidates_for_url(normalized)
    allowed = list(allowed_providers or ())
    for name in candidates:
        if name in allowed:
            return normalized, name, None
    return normalized, None, BatchError(
        BatchErrorCode.PROVIDER_NOT_ALLOWED,
        f"{domain or 'host'} is not on the batch provider allowlist ({', '.join(allowed) or 'empty'}).",
    )


ProcessFn = Callable[[str], Awaitable[ClipResult]]
UpdateFn = Callable[[BatchJob, BatchItem], Awaitable[None]]
SleepFn = Callable[[float], Awaitable[None]]


class BatchAgent:
    """In-memory batch job manager. One active job per owner."""

    def __init__(
        self,
        config: BatchConfig,
        process: ProcessFn,
        *,
        sleep: SleepFn = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = lambda: random.uniform(0, 0.25),
    ) -> None:
        self.config = config
        self._process = process
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter
        self._jobs: dict[str, BatchJob] = {}
        self._latest_by_owner: dict[int, str] = {}
        self._ids = itertools.count(1)
        self._semaphore = asyncio.Semaphore(max(1, config.concurrency))
        self._rate_lock = asyncio.Lock()
        self._last_start: Optional[float] = None

    # ── job lifecycle ────────────────────────────────────────────────
    def create_job(self, owner_id: int, urls: list[str]) -> BatchJob:
        if not self.config.enabled:
            raise BatchError(BatchErrorCode.DISABLED, "The batch agent is disabled (BATCH_AGENT_ENABLED).")
        cleaned = [u.strip() for u in urls if u and u.strip()]
        cleaned = list(dict.fromkeys(cleaned))
        if not cleaned:
            raise BatchError(BatchErrorCode.EMPTY, "Send at least one URL.")
        if len(cleaned) > self.config.max_urls:
            raise BatchError(
                BatchErrorCode.TOO_MANY_URLS,
                f"Too many URLs ({len(cleaned)}); the limit is {self.config.max_urls}.",
            )
        current = self.get_job(owner_id)
        if current and current.is_active:
            raise BatchError(
                BatchErrorCode.JOB_ALREADY_ACTIVE,
                f"Job {current.job_id} is still running. Use /batch cancel first.",
            )
        items = []
        for i, raw in enumerate(cleaned, start=1):
            norm, provider, err = classify_batch_url(raw, self.config.allowed_providers)
            item = BatchItem(index=i, url=norm, provider=provider)
            if err:
                item.status, item.error = ItemStatus.REJECTED, err
            items.append(item)
        job = BatchJob(job_id=f"b{next(self._ids)}", owner_id=owner_id, items=items)
        self._jobs[job.job_id] = job
        self._latest_by_owner[owner_id] = job.job_id
        return job

    def start(self, job: BatchJob, on_update: Optional[UpdateFn] = None) -> asyncio.Task:
        job.task = asyncio.create_task(self.run(job, on_update))
        return job.task

    def get_job(self, owner_id: int) -> Optional[BatchJob]:
        jid = self._latest_by_owner.get(owner_id)
        return self._jobs.get(jid) if jid else None

    def cancel(self, owner_id: int) -> BatchJob:
        job = self.get_job(owner_id)
        if not job or not job.is_active:
            raise BatchError(BatchErrorCode.NO_ACTIVE_JOB, "There is no running batch job to cancel.")
        job.status = JobStatus.CANCELLED
        for item in job.items:
            if item.status not in TERMINAL_ITEM_STATES and item.status != ItemStatus.RUNNING:
                item.status = ItemStatus.CANCELLED
                item.error = BatchError(BatchErrorCode.CANCELLED, "Cancelled by user.")
        job.finished_at = time.time()
        return job

    # ── execution ───────────────────────────────────────────────────
    async def run(self, job: BatchJob, on_update: Optional[UpdateFn] = None) -> BatchJob:
        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.RUNNING
        pending = [i for i in job.items if i.status == ItemStatus.QUEUED]
        await asyncio.gather(*(self._run_item(job, item, on_update) for item in pending))
        if job.status != JobStatus.CANCELLED:
            job.status = JobStatus.COMPLETED
            job.finished_at = time.time()
        return job

    async def _wait_rate_slot(self) -> None:
        async with self._rate_lock:
            now = self._clock()
            if self._last_start is not None:
                wait = self.config.min_interval_seconds - (now - self._last_start)
                if wait > 0:
                    await self._sleep(wait)
            self._last_start = self._clock()

    def backoff_delay(self, attempt: int) -> float:
        base = self.config.retry_base_seconds * (2 ** (attempt - 1))
        return min(self.config.retry_max_seconds, base) + self._jitter()

    async def _notify(self, on_update, job, item) -> None:
        if on_update is None:
            return
        try:
            await on_update(job, item)
        except Exception:  # noqa: BLE001 - progress reporting must never kill the job
            logger.exception("batch.on_update failed job=%s item=%s", job.job_id, item.index)

    async def _run_item(self, job: BatchJob, item: BatchItem, on_update) -> None:
        async with self._semaphore:
            while True:
                if job.status == JobStatus.CANCELLED:
                    if item.status not in TERMINAL_ITEM_STATES:
                        item.status = ItemStatus.CANCELLED
                    return
                await self._wait_rate_slot()
                if job.status == JobStatus.CANCELLED:
                    item.status = ItemStatus.CANCELLED
                    return
                item.attempts += 1
                item.status = ItemStatus.RUNNING
                await self._notify(on_update, job, item)
                try:
                    result = await self._process(item.url)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("batch item crashed job=%s item=%s", job.job_id, item.index)
                    result = None
                    err = BatchError(BatchErrorCode.PIPELINE_ERROR, f"Unexpected error: {type(exc).__name__}")
                    retryable = True
                else:
                    item.result = result
                    if result.status == ClipStatus.SUCCESS:
                        item.status, item.error = ItemStatus.DONE, None
                        await self._notify(on_update, job, item)
                        return
                    err = BatchError(BatchErrorCode.PIPELINE_ERROR, result.rejection_message or result.status.value)
                    # Validation errors are deterministic; provider errors may be transient.
                    retryable = result.status == ClipStatus.PROVIDER_ERROR
                item.error = err
                if retryable and item.attempts <= self.config.max_retries:
                    item.status = ItemStatus.RETRYING
                    await self._notify(on_update, job, item)
                    await self._sleep(self.backoff_delay(item.attempts))
                    continue
                item.status = ItemStatus.FAILED
                await self._notify(on_update, job, item)
                return

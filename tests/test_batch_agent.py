import asyncio

import pytest

from core.models import ClipResult, ClipStatus, ProcessedMedia, RejectionReason
from services.batch_agent import (
    BatchAgent,
    BatchConfig,
    BatchError,
    BatchErrorCode,
    ItemStatus,
    JobStatus,
    classify_batch_url,
    is_admin,
)

YT = "https://www.youtube.com/watch?v=abc123"


def ok(url):
    return ClipResult(status=ClipStatus.SUCCESS, original_url=url, processed_media=ProcessedMedia(file_path="/tmp/x.mp4"))


def provider_err(url):
    return ClipResult(status=ClipStatus.PROVIDER_ERROR, original_url=url,
                      rejection_reason=RejectionReason.PROVIDER_ERROR, rejection_message="boom")


class FakeSleep:
    def __init__(self):
        self.calls = []

    async def __call__(self, s):
        self.calls.append(s)


def make_agent(process, **cfg):
    base = dict(allowed_providers=("youtube", "direct"), min_interval_seconds=0, retry_base_seconds=1, max_retries=2)
    base.update(cfg)
    sleep = FakeSleep()
    agent = BatchAgent(BatchConfig(**base), process, sleep=sleep, jitter=lambda: 0.0)
    return agent, sleep


def test_admin_gate_denies_by_default():
    assert is_admin(1, []) is False
    assert is_admin(None, [1]) is False
    assert is_admin(1, [1, 2]) is True
    assert is_admin(3, [1, 2]) is False


@pytest.mark.parametrize("url", [
    "https://open.spotify.com/track/xyz",
    "https://music.apple.com/us/album/x/1",
    "https://soundcloud.com/a/b",
    "https://on.soundcloud.com/abc",
    "https://music.youtube.com/watch?v=abc",
])
def test_streaming_hosts_blocked(url):
    _, provider, err = classify_batch_url(url, ("youtube", "direct"))
    assert provider is None
    assert err.code == BatchErrorCode.BLOCKED_HOST


def test_allowlist_enforced():
    _, p, err = classify_batch_url("https://www.tiktok.com/@a/video/1", ("youtube",))
    assert err.code == BatchErrorCode.PROVIDER_NOT_ALLOWED
    _, p, err = classify_batch_url(YT, ("youtube",))
    assert p == "youtube" and err is None
    _, p, err = classify_batch_url(YT, ())
    assert err.code == BatchErrorCode.PROVIDER_NOT_ALLOWED


def test_invalid_url():
    _, _, err = classify_batch_url("not a url", ("youtube",))
    assert err.code == BatchErrorCode.INVALID_URL


def test_create_job_limits_and_dedup():
    agent, _ = make_agent(None, max_urls=2)
    with pytest.raises(BatchError) as e:
        agent.create_job(1, [])
    assert e.value.code == BatchErrorCode.EMPTY
    with pytest.raises(BatchError) as e:
        agent.create_job(1, ["https://youtu.be/a", "https://youtu.be/b", "https://youtu.be/c"])
    assert e.value.code == BatchErrorCode.TOO_MANY_URLS
    job = agent.create_job(1, ["https://youtu.be/a", "https://youtu.be/a"])
    assert len(job.items) == 1


def test_disabled():
    agent, _ = make_agent(None, enabled=False)
    with pytest.raises(BatchError) as e:
        agent.create_job(1, [YT])
    assert e.value.code == BatchErrorCode.DISABLED


@pytest.mark.asyncio
async def test_runs_items_and_reports_status():
    seen = []

    async def process(url):
        seen.append(url)
        return ok(url)

    agent, _ = make_agent(process)
    job = agent.create_job(7, [YT, "https://open.spotify.com/track/1", "https://example.com/v.mp4"])
    updates = []

    async def on_update(j, item):
        updates.append((item.index, item.status))

    await agent.run(job, on_update)
    assert job.status == JobStatus.COMPLETED
    assert [i.status for i in job.items] == [ItemStatus.DONE, ItemStatus.REJECTED, ItemStatus.DONE]
    assert "spotify" not in " ".join(seen)
    assert (1, ItemStatus.DONE) in updates
    assert job.counts()["done"] == 2
    assert job.to_dict()["items"][1]["error"]["code"] == "blocked_host"


@pytest.mark.asyncio
async def test_retry_with_backoff_then_success():
    calls = {"n": 0}

    async def process(url):
        calls["n"] += 1
        return provider_err(url) if calls["n"] < 3 else ok(url)

    agent, sleep = make_agent(process)
    job = agent.create_job(1, [YT])
    await agent.run(job)
    assert job.items[0].status == ItemStatus.DONE
    assert job.items[0].attempts == 3
    assert sleep.calls == [1.0, 2.0]


@pytest.mark.asyncio
async def test_retries_exhausted_marks_failed():
    async def process(url):
        return provider_err(url)

    agent, sleep = make_agent(process, max_retries=1)
    job = agent.create_job(1, [YT])
    await agent.run(job)
    assert job.items[0].status == ItemStatus.FAILED
    assert job.items[0].attempts == 2
    assert job.items[0].error.code == BatchErrorCode.PIPELINE_ERROR


@pytest.mark.asyncio
async def test_validation_errors_not_retried():
    async def process(url):
        return ClipResult(status=ClipStatus.VALIDATION_ERROR, original_url=url, rejection_message="too long")

    agent, sleep = make_agent(process)
    job = agent.create_job(1, [YT])
    await agent.run(job)
    assert job.items[0].status == ItemStatus.FAILED and job.items[0].attempts == 1
    assert sleep.calls == []


@pytest.mark.asyncio
async def test_exception_in_pipeline_is_contained():
    async def process(url):
        raise RuntimeError("x")

    agent, _ = make_agent(process, max_retries=0)
    job = agent.create_job(1, [YT])
    await agent.run(job)
    assert job.items[0].status == ItemStatus.FAILED


@pytest.mark.asyncio
async def test_rate_limit_interval_applied():
    t = {"now": 0.0}

    async def sleep(s):
        t["now"] += s
        sleeps.append(s)

    sleeps = []

    async def process(url):
        return ok(url)

    agent = BatchAgent(BatchConfig(allowed_providers=("youtube",), min_interval_seconds=5),
                       process, sleep=sleep, clock=lambda: t["now"], jitter=lambda: 0)
    job = agent.create_job(1, ["https://youtu.be/a", "https://youtu.be/b", "https://youtu.be/c"])
    await agent.run(job)
    assert sleeps == [5, 5]


@pytest.mark.asyncio
async def test_concurrency_limit():
    active = {"now": 0, "max": 0}

    async def process(url):
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        await asyncio.sleep(0.01)
        active["now"] -= 1
        return ok(url)

    agent = BatchAgent(BatchConfig(allowed_providers=("youtube",), min_interval_seconds=0, concurrency=2), process)
    job = agent.create_job(1, [f"https://youtu.be/v{i}" for i in range(6)])
    await agent.run(job)
    assert active["max"] == 2
    assert all(i.status == ItemStatus.DONE for i in job.items)


@pytest.mark.asyncio
async def test_cancel_stops_remaining_items():
    gate = asyncio.Event()
    processed = []

    async def process(url):
        processed.append(url)
        await gate.wait()
        return ok(url)

    agent = BatchAgent(BatchConfig(allowed_providers=("youtube",), min_interval_seconds=0), process)
    job = agent.create_job(1, ["https://youtu.be/a", "https://youtu.be/b", "https://youtu.be/c"])
    task = agent.start(job)
    await asyncio.sleep(0.01)
    agent.cancel(1)
    gate.set()
    await task
    assert job.status == JobStatus.CANCELLED
    assert len(processed) == 1
    assert [i.status for i in job.items[1:]] == [ItemStatus.CANCELLED, ItemStatus.CANCELLED]
    with pytest.raises(BatchError) as e:
        agent.cancel(1)
    assert e.value.code == BatchErrorCode.NO_ACTIVE_JOB


@pytest.mark.asyncio
async def test_one_active_job_per_owner():
    gate = asyncio.Event()

    async def process(url):
        await gate.wait()
        return ok(url)

    agent = BatchAgent(BatchConfig(allowed_providers=("youtube",), min_interval_seconds=0), process)
    job = agent.create_job(1, [YT])
    task = agent.start(job)
    with pytest.raises(BatchError) as e:
        agent.create_job(1, [YT])
    assert e.value.code == BatchErrorCode.JOB_ALREADY_ACTIVE
    agent.create_job(2, [YT])  # other owners unaffected
    gate.set()
    await task


def test_settings_defaults(monkeypatch, make_settings):
    for k in ("BATCH_AGENT_ENABLED", "BATCH_ALLOWED_PROVIDERS", "TELEGRAM_ADMIN_IDS"):
        monkeypatch.delenv(k, raising=False)
    s = make_settings()
    assert s.batch_agent_enabled is False
    assert s.batch_allowed_providers == []
    assert s.telegram_admin_ids == []
    cfg = BatchConfig.from_settings(s)
    assert cfg.enabled is False and cfg.allowed_providers == () and cfg.concurrency == 1


def test_settings_parsing(monkeypatch, make_settings):
    monkeypatch.setenv("BATCH_AGENT_ENABLED", "true")
    monkeypatch.setenv("BATCH_ALLOWED_PROVIDERS", "YouTube, direct")
    monkeypatch.setenv("BATCH_CONCURRENCY", "3")
    s = make_settings()
    assert s.batch_agent_enabled is True
    assert s.batch_allowed_providers == ["youtube", "direct"]
    assert s.batch_concurrency == 3

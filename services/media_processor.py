"""
services.media_processor – Media fallback pipeline for Telegram delivery.

Pipeline order (strict):
  1) download
  2) normalize to MP4
  3) validate output
  4) compress if needed
  5) extract short clip fallback
  6) extract audio fallback
  7) metadata preview fallback
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
import shutil
import subprocess
import tempfile
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from config.settings import Settings
from core.models import MediaCandidate, ProcessedMedia
from core.url_safety import redact_url

logger = logging.getLogger(__name__)

BUFFER_FLUSH_BYTES = 1024 * 1024
DOWNLOAD_PROGRESS_LOG_INTERVAL_SECONDS = 8.0
DOWNLOAD_STALL_TIMEOUT_SECONDS = 45.0


class MediaProcessingError(Exception):
    """Raised when all media fallback steps fail."""


class MediaProcessor:
    """Execute an automatic, production-ready media fallback pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        os.makedirs(self._settings.download_dir, exist_ok=True)

    async def process_media(self, candidate: MediaCandidate) -> ProcessedMedia:
        source_url = candidate.url
        created_paths: list[str] = []
        started_at = time.perf_counter()

        try:
            input_path = await self._download_if_needed(candidate)
            if input_path != candidate.local_path:
                created_paths.append(input_path)

            logger.info("[DOWNLOAD] source=%s input=%s", redact_url(source_url), input_path)

            probed_duration = await self._probe_duration_seconds(input_path)
            if probed_duration is not None:
                candidate.duration_seconds = probed_duration
                max_duration = self._settings.clip_max_duration_seconds
                if probed_duration > max_duration:
                    raise MediaProcessingError(
                        f"Video is {self._format_duration(probed_duration)} long, "
                        f"which exceeds the {self._format_duration(max_duration)} trial limit."
                    )

            if await self._is_video_sendable(input_path) and self._is_mp4_path(input_path):
                if await self._is_telegram_compatible_video(input_path):
                    logger.info("[FAST-PASS] using downloadable MP4 directly=%s", input_path)
                    return self._build_media_result(path=input_path, candidate=candidate, media_kind="video")
                else:
                    logger.info("[FAST-PASS] File is MP4 but has incompatible codec or format, forcing normalization")

            current_path = input_path
            compressed_input_path = input_path

            if (
                self._settings.enable_long_video_fast_path
                and (candidate.duration_seconds or 0) >= self._settings.long_video_fast_path_seconds
            ):
                try:
                    fast_path = await self.fast_transcode_for_telegram(input_path, candidate)
                    created_paths.append(fast_path)
                    logger.info("[FAST-PATH] accepted long-video transcode=%s", fast_path)
                    return self._build_media_result(path=fast_path, candidate=candidate, media_kind="video")
                except MediaProcessingError as exc:
                    logger.info("[FAST-PATH] fallback trigger: %s", exc)

            try:
                normalized_path = await self.normalize_to_mp4(input_path)
                created_paths.append(normalized_path)
                current_path = normalized_path
                compressed_input_path = normalized_path
                if await self._is_video_sendable(normalized_path):
                    return self._build_media_result(
                        path=normalized_path,
                        candidate=candidate,
                        media_kind="video",
                    )
            except MediaProcessingError as exc:
                logger.info("[NORMALIZE] fallback trigger: %s", exc)

            try:
                compressed_path = await self.compress_video(compressed_input_path)
                created_paths.append(compressed_path)
                current_path = compressed_path
                logger.info("[COMPRESS] Returning compressed video (size check bypassed for chunking)=%s", compressed_path)
                return self._build_media_result(
                    path=compressed_path,
                    candidate=candidate,
                    media_kind="video",
                )
            except MediaProcessingError as exc:
                logger.info("[COMPRESS] fallback trigger: %s", exc)

            try:
                clip_path = await self.extract_clip(current_path)
                created_paths.append(clip_path)
                current_path = clip_path
                if await self._is_video_sendable(clip_path):
                    return self._build_media_result(
                        path=clip_path,
                        candidate=candidate,
                        media_kind="video",
                    )
            except MediaProcessingError as exc:
                logger.info("[CLIP] fallback trigger: %s", exc)

            try:
                audio_path = await self.extract_audio(current_path)
                created_paths.append(audio_path)
                if await self._is_audio_sendable(audio_path):
                    return self._build_media_result(
                        path=audio_path,
                        candidate=candidate,
                        media_kind="audio",
                    )
            except MediaProcessingError as exc:
                logger.info("[AUDIO] fallback trigger: %s", exc)

            preview = await self.extract_metadata(source_url)
            logger.info("[FALLBACK] returning metadata preview for %s", redact_url(source_url))
            return ProcessedMedia(
                file_path="",
                duration=candidate.duration_seconds,
                size_bytes=0,
                mime_type="application/json",




            )
        except MediaProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MediaProcessingError("Failed to process media through fallback pipeline") from exc
        finally:
            logger.info("[PIPELINE] media processing total_seconds=%.3f", time.perf_counter() - started_at)
            await self._cleanup_intermediate_files(created_paths)

    async def normalize_to_mp4(self, input_path: str) -> str:
        logger.info("[NORMALIZE] input=%s", input_path)
        output_path = self._new_temp_path(".mp4")
        cmd = self._base_ffmpeg_cmd(input_path) + [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_subprocess(cmd, step="NORMALIZE")
        return output_path

    async def compress_video(self, path: str) -> str:
        logger.info("[COMPRESS] input=%s", path)
        output_path = self._new_temp_path(".mp4")
        cmd = self._base_ffmpeg_cmd(path) + [
            "-c:v",
            "libx264",
            "-crf",
            "30",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_subprocess(cmd, step="COMPRESS")
        return output_path

    async def fast_transcode_for_telegram(self, path: str, candidate: MediaCandidate) -> str:
        logger.info("[FAST-PATH] input=%s", path)
        output_path = self._new_temp_path(".mp4")

        duration = max(candidate.duration_seconds or 1.0, 1.0)
        target_bits_per_second = int((self._settings.telegram_target_video_mb * 8 * 1024 * 1024) / duration)
        audio_bitrate = 96_000
        video_bitrate = max(target_bits_per_second - audio_bitrate, 300_000)
        maxrate = int(video_bitrate * 1.25)
        bufsize = maxrate * 2

        cmd = self._base_ffmpeg_cmd(path) + [
            "-vf",
            "scale='min(1280,iw)':-2:flags=bicubic,fps=30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            str(video_bitrate),
            "-maxrate",
            str(maxrate),
            "-bufsize",
            str(bufsize),
            "-c:a",
            "aac",
            "-b:a",
            f"{math.ceil(audio_bitrate / 1000)}k",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_subprocess(cmd, step="FAST-PATH")
        return output_path

    async def apply_free_watermark(self, path: str) -> str:
        logger.info("[WATERMARK] input=%s", path)
        output_path = self._new_temp_path(".mp4")
        text = self._settings.free_watermark_text.replace("\\", "\\\\").replace(":", "\\:")
        watermark_filter = (
            "drawtext="
            f"text='{text}':"
            "x=w-tw-32:y=h-th-30:"
            "fontsize=max(28\\,h/28):"
            "fontcolor=white@0.92:"
            "box=1:"
            "boxcolor=black@0.58:"
            "boxborderw=18"
        )
        cmd = self._base_ffmpeg_cmd(path) + [
            "-vf",
            watermark_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_subprocess(cmd, step="WATERMARK")
        return output_path

    async def extract_clip(self, path: str, clip_seconds: int = 30) -> str:
        logger.info("[CLIP] input=%s seconds=%s", path, clip_seconds)
        output_path = self._new_temp_path(".mp4")
        cmd = self._base_ffmpeg_cmd(path) + [
            "-t",
            str(clip_seconds),
            "-c:v",
            "libx264",
            "-crf",
            "30",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_subprocess(cmd, step="CLIP")
        return output_path

    async def extract_audio(self, path: str) -> str:
        logger.info("[AUDIO] input=%s", path)
        output_path = self._new_temp_path(".mp3")
        cmd = self._base_ffmpeg_cmd(path) + [
            "-vn",
            "-acodec",
            "mp3",
            output_path,
        ]
        await self._run_subprocess(cmd, step="AUDIO")
        return output_path

    async def extract_metadata(self, url: str) -> dict:
        cmd = ["yt-dlp", "--dump-json", "--skip-download", url]
        logger.info("[FALLBACK] metadata extract for %s", redact_url(url))

        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {"title": "Preview unavailable", "webpage_url": url}

        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(proc.stdout)
        return {"title": "Preview unavailable", "webpage_url": url}

    async def _run_subprocess(self, cmd: list[str], step: str) -> None:
        started_at = time.perf_counter()
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=self._settings.processing_timeout_seconds,
            )
            _, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._settings.processing_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise MediaProcessingError(f"[{step}] timed out") from exc
        except (FileNotFoundError, OSError) as exc:
            raise MediaProcessingError(f"[{step}] executable failed") from exc

        duration_seconds = time.perf_counter() - started_at
        logger.info("[%s] subprocess duration_seconds=%.3f", step, duration_seconds)
        if proc.returncode != 0:
            if self._settings.is_development:
                logger.error("[%s] ffmpeg/yt-dlp failed: %s", step, (stderr or b"").decode(errors="ignore").strip())
            raise MediaProcessingError(f"[{step}] command failed")

    async def _is_video_sendable(self, path: str) -> bool:
        def _check(p: str) -> bool:
            try:
                return os.path.getsize(p) <= self._telegram_limit_bytes
            except OSError:
                return False
        return await asyncio.to_thread(_check, path)

    async def _is_audio_sendable(self, path: str) -> bool:
        return await self._is_video_sendable(path)


    @property
    def _telegram_limit_bytes(self) -> int:
        # DEV intentionally uses a lower threshold to exercise fallbacks locally.
        limit_mb = self._settings.telegram_max_upload_mb
        if self._settings.is_development:
            limit_mb = min(limit_mb, 20)
        return limit_mb * 1024 * 1024

    def _new_temp_path(self, suffix: str) -> str:
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self._settings.download_dir)
        os.close(fd)
        return path

    def _base_ffmpeg_cmd(self, input_path: str) -> list[str]:
        cmd = [self._settings.ffmpeg_path, "-y"]
        if self._settings.is_production:
            cmd.extend(["-loglevel", "error", "-hide_banner"])
        cmd.extend(["-i", input_path])
        return cmd

    def _build_media_result(
        self,
        path: str,
        candidate: MediaCandidate,
        media_kind: str,
        mime_type: Optional[str] = None,
    ) -> ProcessedMedia:
        if not mime_type:
            mime_type = "video/mp4" if media_kind == "video" else "audio/mpeg"

        return ProcessedMedia(
            file_path=path,
            duration=candidate.duration_seconds,
            size_bytes=os.path.getsize(path),
            mime_type=mime_type,




        )

    async def _download_if_needed(self, candidate: MediaCandidate) -> str:
        if candidate.local_path:
            return candidate.local_path
        if not candidate.direct_url:
            raise MediaProcessingError("No media URL available for processing")

        parsed = urlparse(candidate.direct_url)
        extension = ".mp4" if parsed.path.endswith(".mp4") else ".bin"
        fd, temp_path = tempfile.mkstemp(suffix=extension, dir=self._settings.download_dir)
        os.close(fd)

        max_download_bytes = self._settings.clip_max_file_size_mb * 1024 * 1024
        upper_limit = max_download_bytes
        candidate_size_hint = candidate.file_size_bytes
        expected_bytes = None
        started_at = time.perf_counter()
        last_progress_log = started_at
        
        headers = {}
        if candidate.extra and "http_headers" in candidate.extra:
            headers = candidate.extra["http_headers"]

        try:
            timeout = httpx.Timeout(
                timeout=DOWNLOAD_STALL_TIMEOUT_SECONDS,
                connect=15.0,
                read=DOWNLOAD_STALL_TIMEOUT_SECONDS,
                write=60.0,
                pool=60.0,
            )
            async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
                async with client.stream("GET", candidate.direct_url) as resp:
                    resp.raise_for_status()
                    headers = getattr(resp, "headers", {})
                    content_length = headers.get("content-length") if hasattr(headers, "get") else None
                    if content_length and content_length.isdigit():
                        try:
                            expected_bytes = int(content_length)
                        except ValueError:
                            expected_bytes = None

                    downloaded = 0
                    with open(temp_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=BUFFER_FLUSH_BYTES * 4):
                            if not chunk:
                                continue
                            downloaded += len(chunk)
                            if downloaded > upper_limit:
                                raise MediaProcessingError("Download size exceeded maximum limit")
                            f.write(chunk)

                            now = time.perf_counter()
                            if now - last_progress_log >= DOWNLOAD_PROGRESS_LOG_INTERVAL_SECONDS:
                                if expected_bytes:
                                    pct = min(int((downloaded / expected_bytes) * 100), 100)
                                    logger.info(
                                        "[DOWNLOAD] progress=%s%% bytes=%s/%s",
                                        pct,
                                        downloaded,
                                        expected_bytes,
                                    )
                                else:
                                    logger.info("[DOWNLOAD] progress bytes=%s", downloaded)
                                last_progress_log = now
            if candidate_size_hint is None:
                logger.info("[DOWNLOAD] no provider size hint; size limit enforced at %.1f MB", self._settings.clip_max_file_size_mb)
            elif expected_bytes is None:
                logger.info(
                    "[DOWNLOAD] provider size hint=%s MB ignored for download cap; enforcing %.1f MB",
                    candidate_size_hint / (1024 * 1024),
                    self._settings.clip_max_file_size_mb,
                )
            elif expected_bytes != candidate_size_hint:
                logger.info(
                    "[DOWNLOAD] content-length=%s differs from provider hint=%s",
                    expected_bytes,
                    candidate_size_hint,
                )
        except Exception:
            with contextlib.suppress(FileNotFoundError):
                os.remove(temp_path)
            raise
        elapsed = time.perf_counter() - started_at
        logger.info(
            "[DOWNLOAD] completed bytes=%s seconds=%.3f mbps=%.2f",
            downloaded,
            elapsed,
            (downloaded * 8 / (1024 * 1024)) / max(elapsed, 0.001),
        )

        return temp_path

    @staticmethod
    def _is_mp4_path(path: str) -> bool:
        return path.lower().endswith(".mp4")

    async def _is_telegram_compatible_video(self, path: str) -> bool:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,pix_fmt",
            "-of", "json", path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode != 0:
                return False
            data = json.loads(stdout.decode("utf-8", errors="ignore"))
            streams = data.get("streams", [])
            if not streams:
                return False
            
            vstream = streams[0]
            if vstream.get("codec_name") != "h264":
                logger.info("[FAST-PASS REJECT] codec_name is not h264: %s", vstream.get("codec_name"))
                return False
                
            pix_fmt = vstream.get("pix_fmt", "")
            if pix_fmt not in ("yuv420p", "yuvj420p"):
                logger.info("[FAST-PASS REJECT] pix_fmt is not yuv420p: %s", pix_fmt)
                return False
                
            return True
        except Exception as exc:
            logger.debug("[FAST-PASS REJECT] ffprobe check failed: %s", exc)
            return False

    async def _probe_duration_seconds(self, path: str) -> Optional[float]:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        except (asyncio.TimeoutError, FileNotFoundError, OSError) as exc:
            logger.warning("[FFPROBE] duration probe unavailable: %s", exc)
            return None

        if proc.returncode != 0:
            return None

        try:
            duration = float(stdout.decode().strip())
        except ValueError:
            return None

        return duration if duration > 0 else None

    @staticmethod
    def _format_duration(seconds: float | int) -> str:
        total_seconds = int(seconds)
        mins, secs = divmod(total_seconds, 60)
        if mins:
            return f"{mins}m{secs:02d}s"
        return f"{secs}s"

    async def _cleanup_intermediate_files(self, paths: list[str]) -> None:
        if self._settings.is_development:
            return
        if paths:
            await asyncio.gather(*(self.cleanup_file(p) for p in paths))

    async def cleanup_file(self, path: Optional[str]) -> None:
        if not path:
            return
        await asyncio.to_thread(self._safe_remove, path)

    @staticmethod
    def _safe_remove(path: str) -> None:
        with contextlib.suppress(FileNotFoundError, PermissionError, IsADirectoryError):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)

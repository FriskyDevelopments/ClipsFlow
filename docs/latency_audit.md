# ClipsFlow End-to-End Latency Audit

## Scope
This audit covers the hot path from media acquisition to Telegram delivery:

1. download/extraction time
2. ffmpeg transcode/compress time
3. temp-file I/O
4. Telegram upload time
5. duplicate/unnecessary work
6. blocking subprocess patterns
7. long-video speed-vs-quality tradeoffs for Telegram playback

---

## Ranked bottlenecks (highest impact first)

1. **Multiple full-file FFmpeg passes** (`normalize_to_mp4` then `compress_video` then `extract_clip`) can trigger repeated full transcodes on the same asset, which scales poorly with duration/resolution.
2. **Subprocess invocation pattern** (`subprocess.run` wrapped in `asyncio.to_thread`) blocks worker threads and buffers complete output; this can reduce concurrency under burst load.
3. **Late Telegram-size convergence** means the pipeline may spend CPU on high-quality outputs that are later compressed again for size.
4. **Download I/O overhead and chunk-write scheduling** can add overhead due to tiny async/thread handoffs during file writes.
5. **Missing upload-stage timing telemetry** made it difficult to determine whether end-to-end latency was dominated by network upload vs media processing.
6. **No direct-MP4 fast-pass** forced unnecessary transcode in scenarios where source was already Telegram-safe.

---

## Files/functions responsible

- `services/media_processor.py`
  - `process_media`: stage orchestration and fallback sequencing.
  - `_download_if_needed`: network + disk write path.
  - `_run_subprocess`: ffmpeg/yt-dlp process execution strategy.
  - `normalize_to_mp4`, `compress_video`, `extract_clip`: repeated transcode-heavy stages.
- `bot/handlers.py`
  - `BotHandlers.handle_link`: Telegram send path and cleanup.
- `config/settings.py`
  - runtime knobs for timeout/size/fast-path behavior.

---

## Measurements added

- Added per-subprocess duration logs in `_run_subprocess`.
- Added download throughput logging (bytes, elapsed seconds, Mbps) in `_download_if_needed`.
- Added end-to-end media-processing total duration in `process_media`.
- Added Telegram upload duration logging in `BotHandlers.handle_link`.

These logs are sufficient to build p50/p95 histograms for each stage with existing log aggregation.

---

## Proposed patches implemented

1. **Long-video Telegram fast path**
   - New one-pass transcode (`fast_transcode_for_telegram`) using constrained bitrate based on clip duration and configurable target MB budget.
   - Triggered for videos above a configurable duration threshold.

2. **Direct MP4 pass-through**
   - If source is already `.mp4` and under Telegram limit, skip transcode entirely.

3. **Async subprocess execution**
   - Replaced threaded `subprocess.run` usage in ffmpeg path with `asyncio.create_subprocess_exec` + timeout-wrapped `communicate`.

4. **Lower-overhead download writes**
   - Increased stream chunk size and removed per-chunk `asyncio.to_thread` calls for local file writes.

5. **Configurable fast-path controls**
   - Added environment-driven settings:
     - `ENABLE_LONG_VIDEO_FAST_PATH`
     - `LONG_VIDEO_FAST_PATH_SECONDS`
     - `TELEGRAM_TARGET_VIDEO_MB`

---

## Validation plan

1. **Functional parity**
   - Run unit tests for media processor + handlers.
   - Add fixture-driven tests for fast-path trigger thresholds and bitrate budget behavior.

2. **Latency benchmark matrix**
   - Test short (<=60s), medium (2–3 min), and long (>=8 min) clips.
   - Track stage timings: download, each ffmpeg stage, Telegram upload.
   - Compare baseline vs patched p50/p95 total latency.

3. **Quality acceptance for Telegram playback**
   - Human-check outputs on mobile client for seekability/start latency.
   - Verify H.264/AAC compatibility and startup behavior from `+faststart`.

4. **Resource profile**
   - Observe CPU utilization and concurrent request throughput under load.
   - Validate no increase in timeout/failure rates.

5. **Safety checks**
   - Ensure file-size compliance with Telegram upload limit and fallback coverage remains intact.

---

## Fast-path design for long videos (Telegram playback optimized)

### Goals
- Minimize end-to-end latency and Telegram rejections.
- Preserve reasonable watch quality for chat playback.
- Avoid archival-grade processing cost.

### Strategy
1. Estimate per-video target bitrate from desired output size budget (`TELEGRAM_TARGET_VIDEO_MB`) and duration.
2. Encode once with H.264 + AAC using `veryfast`, capped resolution (max width 1280), 30fps, yuv420p.
3. Use `-maxrate`/`-bufsize` for bitrate stability and predictable size.
4. Apply `+faststart` for quicker playback start after upload.
5. If still too large, continue existing fallback chain (compress/clip/audio/metadata).

### Tradeoffs
- Lower visual fidelity on high-motion content versus multi-pass/high-quality encode.
- Significant reduction in compute time and file-size variance.
- Better user-perceived latency for Telegram delivery.

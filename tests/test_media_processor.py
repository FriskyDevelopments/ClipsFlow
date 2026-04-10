import os
import subprocess

import pytest

from core.models import MediaCandidate
from services.media_processor import MediaProcessingError, MediaProcessor


@pytest.mark.asyncio
async def test_process_media_runs_ffmpeg(monkeypatch, tmp_path, make_settings):
    settings = make_settings()
    processor = MediaProcessor(settings)

    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00\x00")

    candidate = MediaCandidate(
        url="https://example.com",
        title="Input",
        duration_seconds=10,
        file_size_bytes=1024,
        media_type="video/mp4",
        source="mock",
        local_path=str(input_path),
    )

    called = {"run": False}

    def fake_run(cmd, stdout=None, stderr=None, check=None, **kwargs):
        called["run"] = True
        output_path = cmd[-1]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"\x00" * 10)
        return subprocess.CompletedProcess(cmd, 0)
        
    async def fake_create_subprocess_exec(*args, **kwargs):
        class MockProcess:
            def __init__(self, retcode):
                self.returncode = retcode
            async def communicate(self):
                return b"", b""
        
        output_path = args[-1]
        if "ffprobe" not in args:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 10)
                
        return MockProcess(1 if "ffprobe" in args else 0)

    import asyncio
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(subprocess, "run", fake_run)

    processed = await processor.process_media(candidate)
    assert os.path.exists(processed.file_path)
    await processor.cleanup_file(processed.file_path)


@pytest.mark.asyncio
async def test_process_media_handles_failures(monkeypatch, tmp_path, make_settings):
    settings = make_settings()
    processor = MediaProcessor(settings)

    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00\x00")

    candidate = MediaCandidate(
        url="https://example.com",
        title="Input",
        duration_seconds=10,
        file_size_bytes=1024,
        media_type="video/mp4",
        source="mock",
        local_path=str(input_path),
    )

    def fake_run_fail(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, ["ffmpeg"])

    async def fake_create_subprocess_exec(*args, **kwargs):
        class MockProcess:
            returncode = 1
            async def communicate(self):
                return b"", b""
        return MockProcess()

    import asyncio
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(subprocess, "run", fake_run_fail)

    with pytest.raises(MediaProcessingError):
        await processor.process_media(candidate)

@pytest.mark.asyncio
async def test_threaded_stress_download(monkeypatch, tmp_path, make_settings):
    settings = make_settings()
    settings.clip_max_file_size_mb = 2000  # Allow up to 2GB
    settings.download_dir = str(tmp_path)

    processor = MediaProcessor(settings)

    # 3 candidates of 1.5GB
    candidate1 = MediaCandidate(
        url="https://example.com/1",
        title="Input 1",
        duration_seconds=10,
        file_size_bytes=1024 * 1024 * 1500, # 1.5GB
        media_type="video/mp4",
        source="mock",
        direct_url="https://example.com/video1.mp4"
    )
    candidate2 = MediaCandidate(
        url="https://example.com/2",
        title="Input 2",
        duration_seconds=10,
        file_size_bytes=1024 * 1024 * 1500, # 1.5GB
        media_type="video/mp4",
        source="mock",
        direct_url="https://example.com/video2.mp4"
    )
    candidate3 = MediaCandidate(
        url="https://example.com/3",
        title="Input 3",
        duration_seconds=10,
        file_size_bytes=1024 * 1024 * 1500, # 1.5GB
        media_type="video/mp4",
        source="mock",
        direct_url="https://example.com/video3.mp4"
    )

    class MockResponse:
        def raise_for_status(self):
            pass
        async def aiter_bytes(self, chunk_size=None):
            # simulate 1.5GB total, but yield in 1MB chunks (1500 chunks)
            # to make the test fast, we actually just yield empty bytes,
            # wait, if we yield 1MB of null bytes, it will write 1.5GB to disk!
            # That might fill up tmp_path and be slow in CI.
            # We can mock `asyncio.to_thread(f.write, chunk)` to avoid actual disk I/O,
            # or just yield very few chunks but pretend they are large if we want to trace memory,
            # actually, just yielding smaller chunks but doing the concurrent loop is enough to prove it doesn't crash.
            # Let's yield 15 chunks of 100KB to prove the loop works and concurrency works.
            for _ in range(15):
                yield b"A" * 1024 * 100

    class MockStream:
        async def __aenter__(self):
            return MockResponse()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        def stream(self, method, url):
            return MockStream()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)

    import asyncio

    # Run the downloads concurrently
    paths = await asyncio.gather(
        processor._download_if_needed(candidate1),
        processor._download_if_needed(candidate2),
        processor._download_if_needed(candidate3),
    )

    assert len(paths) == 3
    for path in paths:
        assert str(tmp_path) in path
        import os
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

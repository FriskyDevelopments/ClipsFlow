import asyncio
from typing import Callable

import pytest

from config.settings import Settings, get_settings
from core.models import MediaCandidate


@pytest.fixture
def make_settings(monkeypatch, tmp_path) -> Callable[..., Settings]:
    def _make(**overrides):
        get_settings.cache_clear()
        base = Settings()
        # Apply overrides
        for key, value in overrides.items():
            setattr(base, key, value)
        # Ensure isolated download directory for tests only if not explicitly provided
        if 'download_dir' not in overrides:
            base.download_dir = str(tmp_path / "downloads")
        return base

    return _make


@pytest.fixture
def make_candidate() -> Callable[..., MediaCandidate]:
    def _make(**kwargs) -> MediaCandidate:
        defaults = dict(
            url="https://example.com/clip",
            title="Test Clip",
            duration_seconds=90.0,
            file_size_bytes=10 * 1024 * 1024,
            media_type="video/mp4",
            source="mock",
            direct_url="https://cdn.example.com/clip.mp4",
        )
        defaults.update(kwargs)
        return MediaCandidate(**defaults)

    return _make


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Fail fast with a clear error when pytest-asyncio is not available."""
    if not (config.pluginmanager.hasplugin("pytest_asyncio") or config.pluginmanager.hasplugin("asyncio")):
        raise pytest.UsageError(
            "pytest-asyncio is required to run this test suite. "
            "Install development dependencies: pip install -r requirements-dev.txt"
        )

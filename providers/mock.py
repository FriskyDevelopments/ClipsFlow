"""Mock provider for unit tests and local development."""

from typing import Optional

from core.models import MediaCandidate
from providers.base import BaseProvider


class MockProvider(BaseProvider):
    name = "mock"

    def can_handle(self, url: str) -> bool:
        return "mock.example.com" in url

    async def resolve(self, url: str) -> Optional[MediaCandidate]:
        if "fail=1" in url:
            from providers.base import ProviderError
            raise ProviderError("mock fail", retryable=False)
        if "unavailable=1" in url:
            return None

        # Determine file size to mock based on URL parameters
        size_bytes = 10 * 1024 * 1024  # default 10MB
        if "size_mb=" in url:
            import re
            match = re.search(r"size_mb=(\d+)", url)
            if match:
                size_bytes = int(match.group(1)) * 1024 * 1024

        # Determine duration based on URL parameters
        duration = 30.0  # default 30 seconds
        if "duration=" in url:
            import re
            match = re.search(r"duration=(\d+)", url)
            if match:
                duration = float(match.group(1))

        return MediaCandidate(
            url=url,
            source=self.name,
            title="Mock Clip",
            duration_seconds=duration,
            file_size_bytes=size_bytes,
            media_type="video/mp4",
            direct_url=f"{url}#direct",
            extra={"stable_name": "mock.mp4"},
        )

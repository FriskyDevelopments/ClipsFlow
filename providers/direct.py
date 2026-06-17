"""Direct URL provider for raw media files."""

import logging
from typing import Optional
from urllib.parse import urlparse

from core.media_normalization import normalized_media_descriptor
from core.models import MediaCandidate
from providers.base import BaseProvider

logger = logging.getLogger(__name__)


class DirectProvider(BaseProvider):
    name = "direct"

    def can_handle(self, url: str) -> bool:
        return any(url.lower().endswith(ext) for ext in (".mp4", ".webm", ".mov", ".mkv", ".mp3", ".m4a"))

    async def resolve(self, url: str, proxy: Optional[str] = None) -> Optional[MediaCandidate]:
        parsed = urlparse(url)
        path = parsed.path
        raw_ext = path.rsplit('.', 1)[-1] if '.' in path else ''
        normalized_ext, media_type = normalized_media_descriptor(ext=raw_ext)

        return MediaCandidate(
            url=url,
            source=self.name,
            title=parsed.path.split('/')[-1] or "Direct media",
            media_type=media_type,
            direct_url=url,
            extra={"host": parsed.netloc, "normalized_extension": normalized_ext, "stable_name": f"direct{normalized_ext}"},
        )

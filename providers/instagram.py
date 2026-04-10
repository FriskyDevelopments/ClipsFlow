from __future__ import annotations

from providers.ytdlp_generic import YtDlpProvider


class InstagramProvider(YtDlpProvider):
    name = "instagram"

    def __init__(self) -> None:
        super().__init__(name="instagram", domains=("instagram.com",), subtype_rules={"/reel/": "reel", "/p/": "post"})

from __future__ import annotations

from providers.ytdlp_generic import YtDlpProvider


class TikTokProvider(YtDlpProvider):
    name = "tiktok"

    def __init__(self) -> None:
        super().__init__(name="tiktok", domains=("tiktok.com",), subtype_rules={"/video/": "short"})

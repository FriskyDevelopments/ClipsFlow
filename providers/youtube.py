"""YouTube provider (standard videos + shorts)."""

from __future__ import annotations

from providers.ytdlp_generic import YtDlpProvider


class YouTubeProvider(YtDlpProvider):
    name = "youtube"

    def __init__(self, api_key: str = "", settings=None) -> None:  # backward-compatible signature
        super().__init__(
            name="youtube",
            domains=("youtube.com", "youtu.be", "thisvid.com"),
            subtype_rules={"/shorts/": "short"},
        )



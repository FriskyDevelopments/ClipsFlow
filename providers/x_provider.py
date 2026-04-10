from __future__ import annotations

from providers.ytdlp_generic import YtDlpProvider


class XProvider(YtDlpProvider):
    name = "x"

    def __init__(self) -> None:
        super().__init__(name="x", domains=("x.com", "twitter.com"), subtype_rules={"/status/": "status"})

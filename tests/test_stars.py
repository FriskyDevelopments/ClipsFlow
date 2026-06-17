import pytest

from services.stars import build_pro_stars_payload, parse_pro_stars_payload, send_pro_stars_invoice


def test_pro_stars_payload_round_trip():
    payload = build_pro_stars_payload("telegram", "123")

    assert payload == "cfpro:telegram:123"
    assert parse_pro_stars_payload(payload) == ("telegram", "123")
    assert parse_pro_stars_payload(payload.encode()) == ("telegram", "123")


@pytest.mark.asyncio
async def test_send_pro_stars_invoice_posts_xtr_payload(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 1}}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            requests.append((url, json))
            return FakeResponse()

    monkeypatch.setattr("services.stars.httpx.AsyncClient", FakeClient)

    await send_pro_stars_invoice("TOKEN", 123, "telegram", "123", 250)

    assert requests == [
        (
            "https://api.telegram.org/botTOKEN/sendInvoice",
            {
                "chat_id": 123,
                "title": "ClipsFlow Pro",
                "description": "Clean exports, unlimited clips, and priority processing.",
                "payload": "cfpro:telegram:123",
                "provider_token": "",
                "currency": "XTR",
                "prices": [{"label": "ClipsFlow Pro", "amount": 250}],
                "start_parameter": "pro",
            },
        )
    ]

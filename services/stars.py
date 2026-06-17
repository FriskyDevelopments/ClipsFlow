from __future__ import annotations

import httpx


def build_pro_stars_payload(platform: str, platform_id: str) -> str:
    return f"cfpro:{platform}:{platform_id}"


def parse_pro_stars_payload(payload: bytes | str) -> tuple[str, str] | None:
    text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else payload
    parts = text.split(":")
    if len(parts) != 3 or parts[0] != "cfpro":
        return None
    platform, platform_id = parts[1].strip(), parts[2].strip()
    if not platform or not platform_id:
        return None
    return platform, platform_id


async def send_pro_stars_invoice(
    bot_token: str,
    chat_id: int,
    platform: str,
    platform_id: str,
    stars_amount: int,
) -> None:
    payload = build_pro_stars_payload(platform, platform_id)
    url = f"https://api.telegram.org/bot{bot_token}/sendInvoice"
    body = {
        "chat_id": chat_id,
        "title": "ClipsFlow Pro",
        "description": "Clean exports, unlimited clips, and priority processing.",
        "payload": payload,
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": "ClipsFlow Pro", "amount": stars_amount}],
        "start_parameter": "pro",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        data = response.json()

    if not data.get("ok"):
        description = data.get("description") or "Telegram rejected the Stars invoice."
        raise RuntimeError(description)

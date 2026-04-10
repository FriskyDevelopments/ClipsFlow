import asyncio
import logging
import os
import stripe
from aiohttp import web
from typing import Callable, Awaitable

from services.db import upsert_user, update_user_by_customer_id

logger = logging.getLogger(__name__)

# Callback type: async function taking platform and platform_id
OnUpgradeCallback = Callable[[str, str], Awaitable[None]]

class WebhookServer:
    def __init__(self, on_upgrade: OnUpgradeCallback):
        self.on_upgrade = on_upgrade
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    async def handle_stripe_webhook(self, request: web.Request) -> web.Response:
        payload = await request.read()
        sig_header = request.headers.get("Stripe-Signature")

        if not sig_header:
            return web.json_response({"error": "Missing stripe-signature header"}, status=400)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            logger.error("Invalid payload: %s", e)
            return web.json_response({"error": "Invalid payload"}, status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.error("Invalid signature: %s", e)
            return web.json_response({"error": "Invalid signature"}, status=400)

        event_type = event.get("type")
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            # Assume client_reference_id contains "telegram|USER_ID" or just "USER_ID" defaults to telegram
            client_ref = data_object.get("client_reference_id")
            customer_id = data_object.get("customer")

            if client_ref:
                parts = client_ref.split("|", 1)
                if len(parts) == 2:
                    platform, platform_id = parts[0], parts[1]
                else:
                    # Default to telegram for legacy compatibility
                    platform, platform_id = "telegram", client_ref

                await asyncio.to_thread(upsert_user, platform, platform_id, True, customer_id)
                logger.info("Upgraded %s user %s to pro", platform, platform_id)

                # Trigger messaging callback
                try:
                    await self.on_upgrade(platform, platform_id)
                except Exception as e:
                    logger.error("Failed to trigger on_upgrade callback: %s", e)

        elif event_type == "customer.subscription.deleted":
            customer_id = data_object.get("customer")
            if customer_id:
                users_updated = await asyncio.to_thread(update_user_by_customer_id, customer_id, False)
                for platform, platform_id in users_updated:
                    logger.info("Downgraded %s user %s from pro", platform, platform_id)

        return web.json_response({"received": True})

    def get_app(self) -> web.Application:
        app = web.Application()
        app.router.add_post("/api/webhook", self.handle_stripe_webhook)
        return app

async def start_webhook_server(on_upgrade: OnUpgradeCallback, host: str = "0.0.0.0", port: int = 8080):
    server = WebhookServer(on_upgrade)
    app = server.get_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Webhook server started on http://%s:%d/api/webhook", host, port)
    return runner

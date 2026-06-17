import { NextResponse } from "next/server";
import { getAppUrl, getPlan } from "../../../../lib/billing";
import { getStripe } from "../../../../lib/stripe";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const plan = getPlan(body.planId);
    const priceId = plan ? process.env[plan.stripePriceEnv] : null;

    if (!plan || !priceId) {
      return NextResponse.json(
        { error: "Billing plan is not configured yet." },
        { status: 400 },
      );
    }

    const appUrl = getAppUrl();
    const telegramUserId = body.telegramUserId ? String(body.telegramUserId) : "";
    const username = body.username ? String(body.username) : "";

    const session = await getStripe().checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: priceId, quantity: 1 }],
      client_reference_id: telegramUserId ? `telegram|${telegramUserId}` : undefined,
      success_url: `${appUrl}/miniapp?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${appUrl}/miniapp?checkout=cancelled`,
      allow_promotion_codes: true,
      metadata: {
        plan_id: plan.id,
        platform: "telegram",
        telegram_user_id: telegramUserId,
        telegram_username: username,
      },
      subscription_data: {
        metadata: {
          plan_id: plan.id,
          platform: "telegram",
          telegram_user_id: telegramUserId,
          telegram_username: username,
        },
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    console.error("Unable to create Checkout Session", error);
    return NextResponse.json(
      { error: "Unable to start checkout." },
      { status: 500 },
    );
  }
}

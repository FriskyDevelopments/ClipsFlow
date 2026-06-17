import { NextResponse } from "next/server";
import { getAppUrl } from "../../../../lib/billing";
import { getStripe } from "../../../../lib/stripe";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const customerId = body.stripeCustomerId ? String(body.stripeCustomerId) : "";

    if (!customerId) {
      return NextResponse.json(
        { error: "A Stripe customer id is required to open the billing portal." },
        { status: 400 },
      );
    }

    const portalSession = await getStripe().billingPortal.sessions.create({
      customer: customerId,
      return_url: `${getAppUrl()}/miniapp`,
    });

    return NextResponse.json({ url: portalSession.url });
  } catch (error) {
    console.error("Unable to create billing portal session", error);
    return NextResponse.json(
      { error: "Unable to open billing portal." },
      { status: 500 },
    );
  }
}

import { NextResponse } from "next/server";
import { getStripe } from "../../../../lib/stripe";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  const signature = request.headers.get("stripe-signature");

  if (!webhookSecret || !signature) {
    return NextResponse.json(
      { error: "Stripe webhook is not configured." },
      { status: 400 },
    );
  }

  const payload = await request.text();

  try {
    const event = getStripe().webhooks.constructEvent(
      payload,
      signature,
      webhookSecret,
    );

    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object;
        console.info("Stripe checkout completed", {
          customer: session.customer,
          clientReferenceId: session.client_reference_id,
          planId: session.metadata?.plan_id,
        });
        break;
      }
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const subscription = event.data.object;
        console.info("Stripe subscription changed", {
          customer: subscription.customer,
          status: subscription.status,
        });
        break;
      }
      default:
        console.info("Unhandled Stripe event", event.type);
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error("Invalid Stripe webhook", error);
    return NextResponse.json({ error: "Invalid webhook." }, { status: 400 });
  }
}

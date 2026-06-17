export type BillingPlan = {
  id: "pro";
  name: string;
  priceLabel: string;
  description: string;
  stripePriceEnv: string;
  features: string[];
};

export const paidPlans: BillingPlan[] = [
  {
    id: "pro",
    name: "ClipsFlow Pro",
    priceLabel: "opens after billing setup",
    description: "Clean exports are gated until the live billing account is configured.",
    stripePriceEnv: "STRIPE_PRICE_PRO_MONTHLY",
    features: ["Clean exports", "Longer runway", "Priority processing"],
  },
];

export function getPlan(planId: string | null | undefined): BillingPlan | null {
  return paidPlans.find((plan) => plan.id === planId) ?? null;
}

export function getAppUrl(): string {
  return (
    process.env.NEXT_PUBLIC_APP_URL ||
    process.env.VERCEL_PROJECT_PRODUCTION_URL?.replace(/^/, "https://") ||
    "http://localhost:3000"
  ).replace(/\/$/, "");
}

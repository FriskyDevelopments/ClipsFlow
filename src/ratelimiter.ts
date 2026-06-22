/// <reference types="@cloudflare/workers-types" />

/**
 * Fixed-window rate limiter backed by a Durable Object. One instance is
 * addressed per client key (e.g. IP), giving a single-threaded, strongly
 * consistent counter — the Workers-native replacement for `express-rate-limit`,
 * whose in-process memory counter cannot work across isolates.
 *
 * Request the limiter by POSTing to the DO with `?windowMs=&max=`; it returns
 * `{ allowed, remaining, resetMs }`.
 */
export class RateLimiter implements DurableObject {
  private count = 0;
  private windowStart = 0;

  constructor(private readonly state: DurableObjectState) {}

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const windowMs = Number(url.searchParams.get("windowMs")) || 60_000;
    const max = Number(url.searchParams.get("max")) || 100;
    const now = Date.now();

    // Hydrate counter state once per cold start.
    if (this.windowStart === 0) {
      this.windowStart = (await this.state.storage.get<number>("windowStart")) ?? now;
      this.count = (await this.state.storage.get<number>("count")) ?? 0;
    }

    if (now - this.windowStart >= windowMs) {
      this.windowStart = now;
      this.count = 0;
    }

    this.count += 1;
    await this.state.storage.put({ windowStart: this.windowStart, count: this.count });

    const allowed = this.count <= max;
    return Response.json({
      allowed,
      remaining: Math.max(0, max - this.count),
      resetMs: this.windowStart + windowMs - now,
    });
  }
}

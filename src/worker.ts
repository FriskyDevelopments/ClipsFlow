/// <reference types="@cloudflare/workers-types" />
import { createApi } from "./api.js";
import { D1Store } from "./d1.js";
import { handleInteraction } from "./discord/interactions.js";
import { RateLimiter } from "./ratelimiter.js";

export { RateLimiter };

export interface Env {
  DB: D1Database;
  RATE_LIMITER: DurableObjectNamespace;
  DISCORD_PUBLIC_KEY: string;
  RATE_LIMIT_WINDOW_MS?: string;
  RATE_LIMIT_MAX?: string;
}

/**
 * Ask the per-client rate limiter Durable Object whether this request may
 * proceed. Keyed by the caller's IP so each client gets an independent window.
 */
async function isRateLimited(request: Request, env: Env): Promise<boolean> {
  const ip = request.headers.get("cf-connecting-ip") ?? "anonymous";
  const id = env.RATE_LIMITER.idFromName(ip);
  const stub = env.RATE_LIMITER.get(id);
  const windowMs = env.RATE_LIMIT_WINDOW_MS ?? "60000";
  const max = env.RATE_LIMIT_MAX ?? "100";
  const res = await stub.fetch(
    `https://rate-limiter/?windowMs=${windowMs}&max=${max}`,
    { method: "POST" },
  );
  const { allowed } = (await res.json()) as { allowed: boolean };
  return !allowed;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const store = new D1Store(env.DB);

    // Discord HTTP interactions endpoint (replaces the gateway bot).
    if (request.method === "POST" && url.pathname === "/interactions") {
      if (!env.DISCORD_PUBLIC_KEY) {
        return new Response("DISCORD_PUBLIC_KEY not configured", { status: 503 });
      }
      return handleInteraction(request, store, env.DISCORD_PUBLIC_KEY);
    }

    // Rate-limit the unauthenticated write path, mirroring the old
    // express-rate-limit on POST /api/v1/clips.
    if (request.method === "POST" && url.pathname === "/api/v1/clips") {
      if (await isRateLimited(request, env)) {
        return Response.json({ error: "Too many requests" }, { status: 429 });
      }
    }

    return createApi(store).fetch(request, env);
  },
};

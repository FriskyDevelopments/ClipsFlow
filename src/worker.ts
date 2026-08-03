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
  ENVIRONMENT?: string;
  RELEASE?: string;
}

interface HealthPayload {
  status: "ok" | "not_ready";
  service: "clipsflow";
  version: string;
  environment: string;
  request_id: string;
}

function requestId(request: Request): string {
  return request.headers.get("cf-ray") ?? request.headers.get("x-request-id") ?? crypto.randomUUID();
}

function healthPayload(env: Env, id: string, status: HealthPayload["status"]): HealthPayload {
  return {
    status,
    service: "clipsflow",
    version: env.RELEASE ?? "development",
    environment: env.ENVIRONMENT ?? "development",
    request_id: id,
  };
}

function withOperationalHeaders(response: Response, id: string, env: Env): Response {
  const headers = new Headers(response.headers);
  headers.set("x-request-id", id);
  headers.set("x-clipsflow-release", env.RELEASE ?? "development");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function readinessResponse(env: Env, id: string): Promise<Response> {
  try {
    await env.DB.prepare("SELECT 1 AS ready").first();
    return Response.json(healthPayload(env, id, "ok"));
  } catch {
    return Response.json(healthPayload(env, id, "not_ready"), { status: 503 });
  }
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
    const id = requestId(request);
    const url = new URL(request.url);

    try {
      if (request.method === "GET" && (url.pathname === "/health" || url.pathname === "/healthz")) {
        return withOperationalHeaders(Response.json(healthPayload(env, id, "ok")), id, env);
      }

      if (request.method === "GET" && (url.pathname === "/ready" || url.pathname === "/readyz")) {
        return withOperationalHeaders(await readinessResponse(env, id), id, env);
      }

      const store = new D1Store(env.DB);

      // Discord HTTP interactions endpoint (replaces the gateway bot).
      if (request.method === "POST" && url.pathname === "/interactions") {
        if (!env.DISCORD_PUBLIC_KEY) {
          return withOperationalHeaders(
            new Response("DISCORD_PUBLIC_KEY not configured", { status: 503 }),
            id,
            env,
          );
        }
        return withOperationalHeaders(
          await handleInteraction(request, store, env.DISCORD_PUBLIC_KEY),
          id,
          env,
        );
      }

      // Rate-limit the unauthenticated write path, mirroring the old
      // express-rate-limit on POST /api/v1/clips.
      if (request.method === "POST" && url.pathname === "/api/v1/clips") {
        if (await isRateLimited(request, env)) {
          return withOperationalHeaders(
            Response.json({ error: "Too many requests", request_id: id }, { status: 429 }),
            id,
            env,
          );
        }
      }

      return withOperationalHeaders(await createApi(store).fetch(request, env), id, env);
    } catch (error) {
      console.error("worker_request_failed", {
        request_id: id,
        method: request.method,
        pathname: url.pathname,
        release: env.RELEASE ?? "development",
        error: error instanceof Error ? error.message : "unknown_error",
      });

      return withOperationalHeaders(
        Response.json({ error: "Internal server error", request_id: id }, { status: 500 }),
        id,
        env,
      );
    }
  },
};

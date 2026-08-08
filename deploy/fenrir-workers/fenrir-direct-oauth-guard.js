// Fenrir edge guard — WorkOS AuthKit is the production auth flow for myfenrir.com.
// This worker proxies the SPA from fenrir-bridge.pages.dev, keeps the WorkOS OAuth
// routes (/api/auth/{login,callback}/workos) live — the WorkOS redirect URIs
// registered for "Fenrirs Community bridge" point at those paths on myfenrir.com
// and www.myfenrir.com — and returns 410 for the retired direct-provider routes.
// Deploy this same script to BOTH `fenrir-direct-oauth-guard` and `fenrir-auth-proxy`.
const pagesOrigin = "https://fenrir-bridge.pages.dev";

// Browser origins allowed to make cross-origin calls to this worker. CORS headers
// reflect the request's Origin only when it is on this list (never the worker's
// own origin), always accompanied by Vary: Origin.
export const ALLOWED_ORIGINS = new Set([
  "https://myfenrir.com",
  "https://www.myfenrir.com",
  "https://login.myfenrir.com",
]);

// /api/auth/login/workos, /api/auth/callback/workos (and any subpath) stay live.
export const WORKOS_AUTH_PATH = /^\/api\/auth\/(login|callback)\/workos(\/|$)/;

const jsonHeaders = {
  "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
  "Content-Type": "application/json; charset=utf-8",
  "X-Fenrir-Edge": "direct-oauth-guard",
};

function corsHeaders(request) {
  const origin = request.headers.get("Origin");
  const headers = { Vary: "Origin" };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS";
    headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization";
  }
  return headers;
}

function json(body, init = {}, request) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      ...jsonHeaders,
      ...(request ? corsHeaders(request) : {}),
      ...(init.headers || {}),
    },
  });
}

function disabledDirectOauth(pathname, request) {
  const route = pathname.includes("/callback/") ? "callback" : "login";
  return json(
    {
      ok: false,
      error: "direct_oauth_disabled",
      detail: `This provider route is retired. Sign in through WorkOS AuthKit; only /api/auth/${route}/workos is active.`,
    },
    { status: 410 },
    request
  );
}

async function proxyPagesRoot(request) {
  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, pagesOrigin);
  const proxied = new Request(target, request);
  return fetch(proxied);
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (
      (url.pathname.startsWith("/api/auth/login/") ||
        url.pathname.startsWith("/api/auth/callback/")) &&
      !WORKOS_AUTH_PATH.test(url.pathname)
    ) {
      return disabledDirectOauth(url.pathname, request);
    }

    return proxyPagesRoot(request);
  },
};

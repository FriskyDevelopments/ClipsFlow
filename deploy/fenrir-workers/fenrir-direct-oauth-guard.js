// Fenrir edge guard. Auth reality: myfenrir.com and FriskyDEV accounts use
// Supabase Auth (the SPA talks to Supabase directly and lands on /auth/callback,
// which this worker simply proxies); the community bridge uses Neon. The old
// direct-provider routes under /api/auth/{login,callback}/ are retired and
// return 410. Everything else proxies to the Pages app.
// Deploy this same script to BOTH `fenrir-direct-oauth-guard` and `fenrir-auth-proxy`.
const pagesOrigin = "https://fenrir-bridge.pages.dev";

// Browser origins allowed to make cross-origin calls to this worker. CORS headers
// reflect the request's Origin only when it is on this list (never the worker's
// own origin), always accompanied by Vary: Origin.
export const ALLOWED_ORIGINS = new Set([
  "https://myfenrir.com",
  "https://www.myfenrir.com",
]);

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
      detail: `The /api/auth/${route}/:provider routes are retired. Sign in on myfenrir.com — authentication is handled by Supabase via the SPA callback route.`,
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
      url.pathname.startsWith("/api/auth/login/") ||
      url.pathname.startsWith("/api/auth/callback/")
    ) {
      return disabledDirectOauth(url.pathname, request);
    }

    return proxyPagesRoot(request);
  },
};

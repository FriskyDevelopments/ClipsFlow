// Fenrir edge guard — proxies the SPA from fenrir-bridge.pages.dev and blocks the
// retired direct-OAuth routes, EXCEPT the WorkOS callback/login paths, which must
// pass through: the WorkOS redirect URIs registered for "Fenrirs Community bridge"
// point at /api/auth/callback/workos on myfenrir.com and www.myfenrir.com.
// Deploy this same script to BOTH `fenrir-direct-oauth-guard` and `fenrir-auth-proxy`.
const pagesOrigin = "https://fenrir-bridge.pages.dev";

const jsonHeaders = {
  "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
  "Content-Type": "application/json; charset=utf-8",
  "X-Fenrir-Edge": "direct-oauth-guard",
};

// /api/auth/login/workos, /api/auth/callback/workos (and any subpath) stay live.
const WORKOS_AUTH_PATH = /^\/api\/auth\/(login|callback)\/workos(\/|$)/;

function json(body, init = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { ...jsonHeaders, ...(init.headers || {}) },
  });
}

function disabledDirectOauth(pathname) {
  const route = pathname.includes("/callback/") ? "callback" : "login";
  return json(
    {
      ok: false,
      error: "direct_oauth_disabled",
      detail: `This provider route is retired. Sign in through WorkOS AuthKit; only /api/auth/${route}/workos is active.`,
    },
    { status: 410 }
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
      return new Response(null, {
        status: 204,
        headers: {
          ...jsonHeaders,
          "Access-Control-Allow-Origin": url.origin,
          "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
      });
    }

    if (
      (url.pathname.startsWith("/api/auth/login/") ||
        url.pathname.startsWith("/api/auth/callback/")) &&
      !WORKOS_AUTH_PATH.test(url.pathname)
    ) {
      return disabledDirectOauth(url.pathname);
    }

    return proxyPagesRoot(request);
  },
};

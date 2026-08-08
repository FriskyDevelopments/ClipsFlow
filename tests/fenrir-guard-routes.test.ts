import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import guard, {
  ALLOWED_ORIGINS,
} from "../deploy/fenrir-workers/fenrir-direct-oauth-guard.js";

const BASE = "https://myfenrir.com";

describe("guard fetch routing", () => {
  const proxied = vi.fn();

  beforeEach(() => {
    proxied.mockReset();
    proxied.mockResolvedValue(new Response("pages", { status: 200 }));
    vi.stubGlobal("fetch", proxied);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const retired = [
    "/api/auth/login/google",
    "/api/auth/login/apple",
    "/api/auth/callback/google",
    "/api/auth/login/workos",
    "/api/auth/callback/workos",
  ];

  it.each(retired)("returns 410 for retired provider route %s", async (path) => {
    const res = await guard.fetch(new Request(`${BASE}${path}`));
    expect(res.status).toBe(410);
    const body = (await res.json()) as { error: string };
    expect(body.error).toBe("direct_oauth_disabled");
    expect(proxied).not.toHaveBeenCalled();
  });

  it("proxies the SPA Supabase callback route to Pages", async () => {
    const res = await guard.fetch(new Request(`${BASE}/auth/callback?code=x`));
    expect(res.status).toBe(200);
    expect(proxied).toHaveBeenCalledTimes(1);
    const forwarded = proxied.mock.calls[0][0] as Request;
    expect(new URL(forwarded.url).hostname).toBe("fenrir-bridge.pages.dev");
    expect(new URL(forwarded.url).search).toBe("?code=x");
  });

  it("proxies non-auth routes through to Pages", async () => {
    const res = await guard.fetch(new Request(`${BASE}/main`));
    expect(res.status).toBe(200);
    expect(proxied).toHaveBeenCalledTimes(1);
  });

  it("reflects an allowlisted Origin on preflight with Vary: Origin", async () => {
    const res = await guard.fetch(
      new Request(`${BASE}/api/state`, {
        method: "OPTIONS",
        headers: { Origin: "https://www.myfenrir.com" },
      })
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(
      "https://www.myfenrir.com"
    );
    expect(res.headers.get("Vary")).toBe("Origin");
  });

  it("omits Access-Control-Allow-Origin for a non-allowlisted Origin", async () => {
    const res = await guard.fetch(
      new Request(`${BASE}/api/state`, {
        method: "OPTIONS",
        headers: { Origin: "https://evil.example.com" },
      })
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
    expect(res.headers.get("Vary")).toBe("Origin");
  });

  it("keeps the production origins on the allowlist", () => {
    for (const origin of ["https://myfenrir.com", "https://www.myfenrir.com"]) {
      expect(ALLOWED_ORIGINS.has(origin)).toBe(true);
    }
  });
});

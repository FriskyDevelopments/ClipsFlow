import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import guard, {
  WORKOS_AUTH_PATH,
  ALLOWED_ORIGINS,
} from "../deploy/fenrir-workers/fenrir-direct-oauth-guard.js";

const BASE = "https://myfenrir.com";

describe("WORKOS_AUTH_PATH route matrix", () => {
  const live = [
    "/api/auth/login/workos",
    "/api/auth/callback/workos",
    "/api/auth/login/workos/",
    "/api/auth/callback/workos/extra",
  ];
  const retired = [
    "/api/auth/login/google",
    "/api/auth/login/apple",
    "/api/auth/callback/google",
    "/api/auth/login/workosx",
    "/api/auth/callback/workosx",
    "/api/auth/callback/notworkos",
  ];

  it.each(live)("matches live WorkOS path %s", (path) => {
    expect(WORKOS_AUTH_PATH.test(path)).toBe(true);
  });

  it.each(retired)("does not match retired/near-miss path %s", (path) => {
    expect(WORKOS_AUTH_PATH.test(path)).toBe(false);
  });
});

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

  it("returns 410 for retired provider login routes", async () => {
    const res = await guard.fetch(new Request(`${BASE}/api/auth/login/google`));
    expect(res.status).toBe(410);
    const body = await res.json();
    expect(body.error).toBe("direct_oauth_disabled");
    expect(proxied).not.toHaveBeenCalled();
  });

  it("returns 410 for near-miss workosx callback", async () => {
    const res = await guard.fetch(new Request(`${BASE}/api/auth/callback/workosx`));
    expect(res.status).toBe(410);
    expect(proxied).not.toHaveBeenCalled();
  });

  it("proxies the WorkOS callback through to Pages", async () => {
    const res = await guard.fetch(
      new Request(`${BASE}/api/auth/callback/workos?code=x&state=y`)
    );
    expect(res.status).toBe(200);
    expect(proxied).toHaveBeenCalledTimes(1);
    const forwarded = proxied.mock.calls[0][0] as Request;
    expect(new URL(forwarded.url).hostname).toBe("fenrir-bridge.pages.dev");
    expect(new URL(forwarded.url).search).toBe("?code=x&state=y");
  });

  it("proxies non-auth routes through to Pages", async () => {
    const res = await guard.fetch(new Request(`${BASE}/main`));
    expect(res.status).toBe(200);
    expect(proxied).toHaveBeenCalledTimes(1);
  });

  it("reflects an allowlisted Origin on preflight with Vary: Origin", async () => {
    const res = await guard.fetch(
      new Request(`${BASE}/api/auth/callback/workos`, {
        method: "OPTIONS",
        headers: { Origin: "https://login.myfenrir.com" },
      })
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(
      "https://login.myfenrir.com"
    );
    expect(res.headers.get("Vary")).toBe("Origin");
  });

  it("omits Access-Control-Allow-Origin for a non-allowlisted Origin", async () => {
    const res = await guard.fetch(
      new Request(`${BASE}/api/auth/callback/workos`, {
        method: "OPTIONS",
        headers: { Origin: "https://evil.example.com" },
      })
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
    expect(res.headers.get("Vary")).toBe("Origin");
  });

  it("keeps every production origin on the allowlist", () => {
    for (const origin of [
      "https://myfenrir.com",
      "https://www.myfenrir.com",
      "https://login.myfenrir.com",
    ]) {
      expect(ALLOWED_ORIGINS.has(origin)).toBe(true);
    }
  });
});

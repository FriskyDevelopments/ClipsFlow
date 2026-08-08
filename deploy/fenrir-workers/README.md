# Fenrir edge guard — deploy notes

**Auth reality (2026-08-08):** myfenrir.com and FriskyDEV accounts authenticate with
**Supabase Auth** (project `FriskyDEV`, `yqevglppbhuoxxfsfnih`) — the SPA talks to
Supabase directly and returns through the SPA's `/auth/callback` route, which the
guard simply proxies. The **community bridge** (`gate.myfenrir.com`) uses **Neon**.
WorkOS is retired and plays no part in production auth.

## What the guard does

`fenrir-direct-oauth-guard.js` (deploy the same script to BOTH the
`fenrir-direct-oauth-guard` and `fenrir-auth-proxy` workers):

- proxies the SPA from `fenrir-bridge.pages.dev` (including `/auth/callback`);
- returns **410 `direct_oauth_disabled`** for the retired
  `/api/auth/{login,callback}/:provider` routes, pointing users at the Supabase
  SPA flow;
- reflects CORS only for the allowlisted browser origins (`myfenrir.com`, `www`),
  with `Vary: Origin` — never the worker's own origin.

Compared to the currently deployed Aug 5 bundle this adds the origin-allowlisted
CORS handling and an accurate 410 message; route behavior is otherwise identical.

## Deploy

```bash
# from a ClipsFlow checkout of this branch, with wrangler authenticated
npx wrangler deploy deploy/fenrir-workers/fenrir-direct-oauth-guard.js \
  --name fenrir-direct-oauth-guard --compatibility-date 2026-08-01
npx wrangler deploy deploy/fenrir-workers/fenrir-direct-oauth-guard.js \
  --name fenrir-auth-proxy --compatibility-date 2026-08-01
```

## Verify

```bash
curl -si https://myfenrir.com/api/auth/login/google | head -1   # 410 (retired)
curl -si https://myfenrir.com/main | head -1                    # 200 via Pages proxy
```

Then sign in on myfenrir.com (Supabase → provider → `/auth/callback`) and confirm
the session lands. Route tests live in `tests/fenrir-guard-routes.test.ts`
(`npm test`).

## Related (separate bugs, still open)

- `fenrir-mcp-beta`: its bearer-token gate runs before route dispatch, so the
  intended-public `/api/health` and `/api/auth/me` handlers are unreachable; move
  the `mcpAuthFailure(...)` check inside the `isMcpEndpoint(url.pathname)` branch,
  and add `"https://myfenrir.com"` (apex) to its `DEFAULT_ALLOWED_ORIGINS`.
- `myfenrir-login` (login.myfenrir.com) is a retired WorkOS-era worker that sets a
  forgeable unsigned `fenrir_workos_user` email cookie — decommission it or point
  the subdomain at the SPA login.

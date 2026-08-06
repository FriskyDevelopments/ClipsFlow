# Fenrir login fix — deploy steps

Three blockers are stacked on the WorkOS login path. This directory carries the fix
for #1; #2 and #3 are WorkOS dashboard toggles (or one connector call each once the
WorkOS MCP connector is reconnected).

## 1. Edge guard 410s the WorkOS callback (deploy `fenrir-direct-oauth-guard.js`)

The workers `fenrir-auth-proxy` and `fenrir-direct-oauth-guard` (both deployed
2026-08-05 17:11 UTC, identical bundles) return **410 `direct_oauth_disabled`** for
everything under `/api/auth/callback/` — including the registered WorkOS redirect
URIs `https://myfenrir.com/api/auth/callback/workos` and the `www` variant. The
patched script in this directory exempts `/api/auth/{login,callback}/workos` and
proxies them through to the Pages app like every other route.

```bash
# from a machine with wrangler authenticated against account e2a7eccb…
npx wrangler deploy deploy/fenrir-workers/fenrir-direct-oauth-guard.js \
  --name fenrir-direct-oauth-guard --compatibility-date 2026-08-01
npx wrangler deploy deploy/fenrir-workers/fenrir-direct-oauth-guard.js \
  --name fenrir-auth-proxy --compatibility-date 2026-08-01
```

## 2. Enable the social providers in WorkOS

Environment **"Fenrirs Community bridge"** (`environment_01KT7NWYB12QG2NJH64R5EACFQ`,
client `client_01KT7NWYWB256XP0V00PX1YW01`) has Apple, Google, and Microsoft OAuth
**all disabled**, while the login page at `login.myfenrir.com` offers exactly those
three buttons. In the WorkOS dashboard → Authentication → Social login: add each
provider's OAuth client credentials and enable it. Until then only "More sign-in
options" (AuthKit with Magic Auth email codes) can work.

## 3. Register the login worker's redirect URI

`myfenrir-login` defaults to `redirect_uri=https://login.myfenrir.com/auth/callback`,
which is **not** in the environment's redirect URI list (current entries:
`https://myfenrir.com/auth/callback` (default), `https://myfenrir.com/api/auth/callback/workos`,
`https://www.myfenrir.com/api/auth/callback/workos`). Add
`https://login.myfenrir.com/auth/callback` in WorkOS dashboard → Redirects — or set
the worker's `WORKOS_REDIRECT_URI` secret to one of the registered URIs instead.

## Also worth doing (same stack, separate bugs)

- `fenrir-mcp-beta`: move the `mcpAuthFailure(...)` check inside the
  `isMcpEndpoint(url.pathname)` branch so public routes (`/api/health`,
  `/api/auth/me`) stop requiring the bot bearer token, and add
  `"https://myfenrir.com"` (apex) to `DEFAULT_ALLOWED_ORIGINS`.
- The `fenrir_workos_user` cookie set by `myfenrir-login` is an unsigned plain
  email on `.myfenrir.com` — forgeable; nothing server-side should trust it as a
  session credential.

## Verify after deploying

```bash
curl -i https://myfenrir.com/api/auth/callback/workos   # expect proxy/redirect, NOT 410
curl -i https://myfenrir.com/api/auth/login/google      # still 410 (intentionally retired)
```
Then run a full login from `login.myfenrir.com` and confirm a user appears in the
WorkOS environment (user list is currently empty — zero logins have ever completed).

# Fenrir login — debug findings (2026-08-06)

Investigation of why login on **myfenrir.com** (Fenrir Bridge) is broken. The Fenrir
edge stack lives in Cloudflare Workers (account `e2a7eccb…`, `hrgrrtks2p`), not in this
repo, so findings below were pulled from the **deployed worker bundles**, the
`fenrir-bridge` D1 database, and Supabase logs. Live HTTP probing was not possible from
this sandbox (egress allowlist), so findings F1–F3 each include a verification command
to run from any normal machine (F4 and F5 are configuration/data observations verified
directly against WorkOS and D1).

> **Update (2026-08-06): the production auth decision is WorkOS AuthKit.** Any
> Supabase-migration guidance below (notably in F3/F4) is historical context from
> before that decision — keep WorkOS, do not migrate the login to Supabase or Neon
> Auth. The current fix path lives in `deploy/fenrir-workers/README.md`.

## Timeline signal

Five Fenrir workers were redeployed in one batch on **2026-08-05 between 17:09 and
17:11 UTC**: `fenrir-gate-router`, `fenrir-mcp-beta`, `fenrir-stars-payments`,
`fenrir-auth-proxy` (newly created), `fenrir-direct-oauth-guard`. The last successful
signup recorded in D1 `app_users` is **2026-08-05 09:55 UTC** — i.e. before that batch.
Supabase (`FriskyDEV`, `yqevglppbhuoxxfsfnih`) shows constant REST traffic from the
Telegram bots but **zero `/auth/v1/*` requests and zero auth-service log lines in the
last 24 h** — nobody is even *reaching* the OAuth step.

## Reconstructed topology

| Host / route | Worker | Behavior |
|---|---|---|
| `myfenrir.com` (SPA) | `fenrir-auth-proxy` / `fenrir-direct-oauth-guard` (identical bundles) | Proxies `fenrir-bridge.pages.dev`; returns **410 `direct_oauth_disabled`** for `/api/auth/login/:provider` and `/api/auth/callback/:provider` |
| `/api/*`, `/mcp` | `fenrir-mcp-beta` | JSON API + MCP beta server (its own "beta plan" says routing live `/api/*` here is the next phase) |
| `login.myfenrir.com` | `myfenrir-login` | Legacy **WorkOS AuthKit** flow; on success sets unsigned `fenrir_workos_user=<email>` cookie on `.myfenrir.com` |
| `myfenrir.com/gate/*` | `fenrir-gate-router` → `fenrir-stars-payments` | Telegram webhook, Stars billing, account linking |
| Data | D1 `fenrir-bridge` (`1238059e…`) | `app_users` (25 rows), `telegram_account_link_codes`, `telegram_identity_links`, billing tables |

## Findings (ranked)

### F1 — `fenrir-mcp-beta` auth-gates its *public* routes (login state check can never succeed)

In the worker's `fetch()`, `mcpAuthFailure(request, env)` runs **before** route
dispatch. So every route — including `/api/health` and `/api/auth/me`, which have
deliberate public handlers further down (`/api/auth/me` returns
`{ok:true, authenticated:false}`) — requires `Authorization: Bearer
<FRISKY_BOT_API_TOKEN>`. Browsers never send that header, so:

- token configured → every SPA call to `/api/auth/me` returns **401 `mcp_auth_required`**;
- token not configured → **503 `mcp_auth_not_configured`**.

Either way the SPA's session check always fails and the user permanently appears
logged out. **Fix:** enforce the bearer check only for the MCP endpoints:

```js
// in fetch(), replace the unconditional gate:
if (isMcpEndpoint(url.pathname)) {
  const authFailure = mcpAuthFailure(request, env);
  if (authFailure) return authFailure;
  return handleMcp(request, env, url);
}
```

Verify: `curl -i https://myfenrir.com/api/auth/me` — a JSON 401
`mcp_auth_required` confirms this worker is on the live route and gating browsers.

### F2 — apex origin `https://myfenrir.com` missing from the CORS allowlist

`DEFAULT_ALLOWED_ORIGINS` in `fenrir-mcp-beta` contains `https://www.myfenrir.com` and
`https://auth.myfenrir.com` plus localhost entries — but **not the apex**
`https://myfenrir.com`, which is exactly where the Telegram bot buttons send users
("Open app → https://myfenrir.com"). Any credentialed/cross-origin fetch carrying
`Origin: https://myfenrir.com` is rejected with **403 `origin_not_allowed`** before
auth is even considered. **Fix:** add the apex to `DEFAULT_ALLOWED_ORIGINS` (or set the
`MCP_ALLOWED_ORIGINS` env var).

Verify: `curl -i -H "Origin: https://myfenrir.com" https://myfenrir.com/api/health`.

### F3 — SPA login buttons dead-end into the 410 guard

`fenrir-auth-proxy` / `fenrir-direct-oauth-guard` intentionally return **410
`direct_oauth_disabled`** for `/api/auth/login/:provider` and
`/api/auth/callback/:provider`, with the message "Register OAuth callbacks in Supabase
and use the SPA callback route instead." If the deployed Pages SPA
(`fenrir-bridge.pages.dev`) still links its provider buttons to those routes, clicking
"Continue with Google/Apple/…" renders raw JSON 410. The **zero Supabase auth traffic**
strongly supports that the Supabase-side flow was never wired up: the old direct routes
were disabled before the replacement (supabase-js `signInWithOAuth` + registered
redirect URLs + SPA `/auth/callback` route) went live.

**Fix (historical — superseded):** the Supabase `signInWithOAuth` route was
considered here before the WorkOS decision. The current fix keeps WorkOS: exempt
`/api/auth/{login,callback}/workos` from the guard's 410 (done in
`deploy/fenrir-workers/fenrir-direct-oauth-guard.js`) and point the SPA's provider
buttons at the WorkOS AuthKit flow.

Verify: open the login page and inspect the provider buttons' hrefs; and
`curl -i https://myfenrir.com/api/auth/login/google` (expect the 410 today).

### F4 — two parallel auth stacks that don't share a session

`login.myfenrir.com` still runs the June-era **WorkOS AuthKit** worker. On success it
sets `fenrir_workos_user=<email>` on `.myfenrir.com` and redirects to `/main`. The SPA
and API layer expect a **Supabase** session, so even a fully successful WorkOS login
leaves the user "logged out" in the app — a classic split-brain that looks exactly like
"login is broken" to the user.

Security note: that cookie is an **unsigned plain email** — anyone can forge
`fenrir_workos_user=admin@example.com`. Nothing should trust it. Since WorkOS is the
production auth (see the update note above), the fix is to make the WorkOS callback
mint a real signed/D1-backed session for `.myfenrir.com` that the SPA and API layer
both honor — not to retire WorkOS.

### F5 — Telegram identity linking split-brain (D1 vs Supabase)

`fenrir-stars-payments` writes account links to **D1** (`telegram_identity_links`,
claimed via `/start link_<code>`), while other services (FriskyClaw bot) read
`telegram_identity_links` from **Supabase REST**. Current D1 state: **111 link codes,
all `pending` (newest 2026-05-25), and 0 rows in `telegram_identity_links`** — the D1
linking path has never completed once, and even if it did, the Supabase-side readers
would not see it. Pick one store (or replicate) and confirm the "link generated in
MyFenrir → claimed in Telegram" loop end-to-end.

## Suggested order of operations

1. Deploy the patched guard (`deploy/fenrir-workers/`) so the WorkOS callback routes
   stop returning 410 (F3).
2. Apply F1 (move the auth gate onto `/mcp` only) and F2 (add apex origin) to
   `fenrir-mcp-beta` — both are two-line edits and unblock `/api/auth/me`.
3. In WorkOS: register `https://login.myfenrir.com/auth/callback` and enable the
   Apple/Google/Microsoft providers with their credentials (F4 prerequisites).
4. Harden the WorkOS session (signed cookie or D1-backed session, F4) and unify
   identity-link storage (F5).
5. Re-test: `/api/health` 200 JSON, `/api/auth/me` 200 `{authenticated:false}` for
   anonymous, provider button → WorkOS → callback → session present, and a fresh row
   in `app_users`.

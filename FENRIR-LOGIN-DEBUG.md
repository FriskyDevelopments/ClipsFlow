# Fenrir login — debug findings (2026-08-06)

Investigation of why login on **myfenrir.com** (Fenrir Bridge) is broken. The Fenrir
edge stack lives in Cloudflare Workers (account `e2a7eccb…`, `hrgrrtks2p`), not in this
repo, so findings below were pulled from the **deployed worker bundles**, the
`fenrir-bridge` D1 database, and Supabase logs. Live HTTP probing was not possible from
this sandbox (egress allowlist), so findings F1–F3 each include a verification command
to run from any normal machine (F4 and F5 are configuration/data observations verified
directly against WorkOS and D1).

> **Update (2026-08-08): production auth is Supabase for myfenrir.com and FriskyDEV
> accounts, and Neon for the community bridge. WorkOS is retired.** As of
> 2026-08-08 the Supabase flow is confirmed working end-to-end (successful Apple
> and Google logins in the auth logs, zero errors in 24 h). Any WorkOS-fix guidance
> below is historical context from an earlier direction that was abandoned. The
> current guard notes live in `deploy/fenrir-workers/README.md`.

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

**Resolution (2026-08-08):** the SPA was wired to Supabase (`signInWithOAuth` →
provider → SPA `/auth/callback`), which the guard proxies untouched — the 410
tombstones on `/api/auth/{login,callback}/:provider` never sit on the live path.
Auth logs confirm successful Apple/Google logins and signups through this flow.

### F4 — two parallel auth stacks that don't share a session

`login.myfenrir.com` still runs the June-era **WorkOS AuthKit** worker. On success it
sets `fenrir_workos_user=<email>` on `.myfenrir.com` and redirects to `/main`. The SPA
and API layer expect a **Supabase** session, so even a fully successful WorkOS login
leaves the user "logged out" in the app — a classic split-brain that looks exactly like
"login is broken" to the user.

Security note: that cookie is an **unsigned plain email** — anyone can forge
`fenrir_workos_user=admin@example.com`. Nothing should trust it. With WorkOS
retired (see the update note above), the fix is to decommission the
`myfenrir-login` worker entirely — or repoint `login.myfenrir.com` at the SPA's
Supabase login — so this cookie stops being minted at all.

### F5 — Telegram identity linking split-brain (D1 vs Supabase)

`fenrir-stars-payments` writes account links to **D1** (`telegram_identity_links`,
claimed via `/start link_<code>`), while other services (FriskyClaw bot) read
`telegram_identity_links` from **Supabase REST**. Current D1 state: **111 link codes,
all `pending` (newest 2026-05-25), and 0 rows in `telegram_identity_links`** — the D1
linking path has never completed once, and even if it did, the Supabase-side readers
would not see it. Pick one store (or replicate) and confirm the "link generated in
MyFenrir → claimed in Telegram" loop end-to-end.

## Suggested order of operations

1. F3 is resolved — Supabase login works end-to-end (see the update note). The
   guard in `deploy/fenrir-workers/` remains an optional refresh: same route
   behavior as production, plus origin-allowlisted CORS and an accurate 410 message.
2. Apply F1 (move the auth gate onto `/mcp` only) and F2 (add apex origin) to
   `fenrir-mcp-beta` — both are two-line edits and unblock `/api/auth/me`.
3. Decommission the retired WorkOS-era `myfenrir-login` worker so the forgeable
   `fenrir_workos_user` cookie stops being minted (F4).
4. Unify identity-link storage between D1 and Supabase (F5).
5. Re-test: `/api/health` 200 JSON, `/api/auth/me` 200 `{authenticated:false}` for
   anonymous, provider button → Supabase → `/auth/callback` → session present.

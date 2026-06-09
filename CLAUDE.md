# Plugin context for future coding agents

If you're a Claude Code (or other AI) instance working in this repo, this file is the fastest way to get your bearings. Read it first.

## Mission

This plugin exists to **drive subscriptions to tlsradar.com**. Every design choice serves that:

- Free anonymous scans and free Beacon cert issuance lower the entry barrier so users install the plugin without an account.
- The cert-issuance → monitoring handoff turns one-off Beacon users into TLS Radar monitor users (the conversion event).
- Monitor cap hits surface a friendly 402 that leads with Starter ($9.99/mo) - the typical upgrade.

When you change something, ask "does this make the funnel smoother or noisier?" If it adds friction at install, login, or cap-hit, it probably regresses conversion.

## Architecture in one paragraph

There is no binary. The plugin is pure configuration + Markdown. Claude Code's MCP client talks to **one** remote MCP server - `tlsradar.com/api/v1/mcp`. Certificate issuance is **proxied server-side** through that server to Beacon (`beacon.tlsradar.com`), so the plugin holds a single connection and a single auth model. Public tools (`scan`, `cert_*`) need no auth; everything else uses Claude Code's built-in OAuth 2.0 + PKCE flow via `/mcp` (the plugin registers dynamically, RFC 7591, the first time the user runs `/mcp`). There is no client-facing Beacon connection and no `BEACON_PLUGIN_TOKEN` anymore - TLS Radar's `Beacon::Client` calls Beacon's REST API server-to-server with the (intentionally public) token it already holds.

**Deliberate architecture decision (the proxy + an independent Beacon).** Beacon is a genuinely independent product with its own users - a free Let's Encrypt issuer that exists partly to drive TLS Radar subscriptions via the cert→monitoring handoff. We *keep the proxy* anyway: the plugin's one-server simplicity is worth the operational coupling (TLS Radar can't issue if Beacon is down). So we accept the "coupled but separate" middle on purpose rather than either folding Beacon into Rails or making the plugin talk to two servers. The clean seam between the two products is the signed `certificate_issued` push, not the proxy. Don't "fix" this by merging the codebases.

## Repo layout

```
.
├── CLAUDE.md                          ← you are here
├── README.md                          ← user-facing install + usage
├── .claude-plugin/plugin.json         ← plugin manifest (name, version, repo URL)
├── .claude-plugin/marketplace.json    ← self-hosting marketplace: `/plugin marketplace add TLS-Radar/tlsradar-claude-plugin` then `/plugin install tlsradar@tlsradar`
├── .mcp.json                          ← MCP server config (ONE remote URL + install-id header)
├── hooks/hooks.json                   ← SessionStart welcome + anonymous install-id mint (one-time)
├── tools/manifest.json                ← SINGLE SOURCE OF TRUTH for tool names + the beacon response `fields` the proxy reads
├── scripts/verify_tool_names.py       ← CI guard (offline): every tool ref is in the manifest
├── scripts/verify_beacon_contract.py  ← live check: Beacon still exposes the manifest's beacon tools AND fields (non-blocking CI)
├── scripts/generate_router.py         ← regenerates SKILL.md's tool table from the manifest (--check in CI)
├── scripts/dns_provider.py            ← tested local helper: set/delete the dns-01 TXT via Cloudflare/Route53 (creds stay local)
├── scripts/dns_provider_test.py       ← unit tests for the gotcha-prone provider logic (root/quoting/payloads)
├── evals/                             ← tool-routing evals (prompt → expected tool); static check runs in CI
├── .github/workflows/verify-contracts.yml ← runs guard + router --check + eval on every PR/push
├── commands/
│   ├── README.md                      ← how to add/edit slash commands
│   ├── tls-scan.md                    ← free anonymous scan (public)
│   ├── tls-cert.md                    ← free LE cert issuance via tlsradar.cert_* (CSR-only, local key)
│   ├── tls-renew.md                   ← cert renewal (usually just cert_create again)
│   ├── tls-monitor.md                 ← list/add/remove monitors (single or bulk)
│   ├── tls-upgrade.md                 ← open pricing page (funnel)
│   └── tls-diagnose.md                ← health check; user-facing debug
└── skills/
    ├── README.md                      ← how to extend / when to use a skill
    └── certificate-monitoring/
        └── SKILL.md                   ← single skill - NL-trigger router (also routes the non-command tools:
                                          expiring, scan_history, me, export, import, team_invite)
```

Only the common funnel/multi-step flows have slash commands now (`tls-scan`, `tls-cert`, `tls-renew`, `tls-monitor`, `tls-upgrade`, `tls-diagnose`). The thin 1:1 data tools (`expiring`, `scan_history`, `me`, `export`, `import`, `team_invite`) are reached by natural language through the skill - fewer command files to keep in sync with the backend.

## The funnel (read carefully)

```
User installs plugin (zero friction)
        ↓
User runs /tls-scan example.com  (anonymous, no account)
        ↓
   "value moment 1" - they see the scan works
        ↓
User runs /tls-cert mydomain.dev  (anonymous, all via the tlsradar server)
   Step 1: tlsradar.cert_create(domain, email)
           → proxies Beacon create_order (sets webhook_url=tlsradar.com/webhooks/beacon),
             PERSISTS BeaconOrder(order_id → email, domain) right here,
             returns {order_id, dns_records}
   Step 2: user publishes TXT records, tlsradar.cert_check_propagation polls until green
   Step 3: openssl generates key+CSR LOCALLY, then
           tlsradar.cert_finalize(order_id, csr_pem)
           → validates + waits for LE + issues, one call → PEM chain (key never left the box)
        ↓
   "value moment 2" - they have a real LE cert; private key stayed local
        ↓
Beacon issuance completes → OnIssued fires →
   Beacon PUSHES to tlsradar.com/api/v1/beacon/certificate_issued
   Headers: X-Beacon-Signature: sha256=<hex over body>, X-Beacon-Event: certificate_issued
   Body: { event, order_id, email, domain, serial, marketing_consent, not_after, occurred_at }
   (carries the EMAIL server-to-server; signed with the shared TLSRADAR_NOTIFY_SECRET)
        ↓
TLS Radar Api::V1::BeaconController#certificate_issued:
   - verifies shared-secret HMAC
   - BeaconOrder already exists (persisted at cert_create) → enqueues BeaconHandoffJob
        ↓
TLS Radar BeaconHandoffJob runs:
   - finds user by email (matches OAuth + email-provider identities)
   - auto-adds host to user's first scan_group (free plan = 1 monitor)
   - sends UserMailer.beacon_handoff_existing  ← conversion email
        ↓
   For anonymous (no existing user) → UserMailer.beacon_handoff_signup
   with magic-link signup URL carrying ?prefill_domain=<domain>
        ↓
User clicks signup link → creates account → dashboard auto-adds monitor on first load
   (DashboardController reads user.metadata["pending_prefill_domain"])
        ↓
User is now a TLS Radar account holder watching a real domain.
That domain's expiry alert in 83 days is the next conversion checkpoint
(7-day free vs 30-day Starter warning window).
```

**The handoff is server-to-server and doubly robust.** `tlsradar.cert_create` (the proxy tool, in `app/services/mcp_services/tools/cert_create.rb`) persists the `BeaconOrder(order_id → email, domain)` mapping at creation time - so the email is known server-side from the start, not dependent on any later call. It also sets the order's `webhook_url` to the TLS Radar host so that when issuance completes, Beacon's `OnIssued` notifier (`beacon/internal/tlsradar/notify.go`, `targetsTLSRadar`) pushes a signed `certificate_issued` to `Api::V1::BeaconController#certificate_issued`, which enqueues `BeaconHandoffJob`. The proxy intentionally does NOT store the per-order webhook secret, so the legacy per-order `/webhooks/beacon` path can't also drive the handoff - the push is the single channel. The old client-side `tlsradar.beacon_order_register` is obsolete (the tool still exists, idempotent, but nothing calls it).

## Contracts you must respect

### TLS Radar MCP tools (`https://tlsradar.com/api/v1/mcp`)

Public (no auth):
- `scan(domain)` - queues an anonymous SSL/TLS scan, returns share_token
- `cert_create(domain, email, challenge?, marketing_consent?)` - proxies Beacon create_order; persists the BeaconOrder mapping. `challenge` is `dns-01` (default; returns `dns_records`; issues domain+www) or `http-01` (returns `http_files`; issues the apex only). Step 1.
- `cert_check_propagation(order_id)` - proxies Beacon check_propagation (DNS resolvers for dns-01, HTTP fetch for http-01). Step 2.
- `cert_finalize(order_id, csr_pem | passphrase, max_wait_seconds?)` - proxies Beacon finalize_order (validate+wait+issue, one call, ~25s cap). Step 3. The plugin passes `csr_pem` (key stays local). **Idempotent for the csr_pem path** - a completed order returns the same stored chain, so a timed-out retry never re-issues.
- `cert_status(order_id)` - proxies Beacon get_order_status; on a completed CSR order it carries `fullchain_pem` so a poll can retrieve the cert.
- `cert_renew(order_id)` - proxies Beacon renew_order (clone by id). Usually use `cert_create` for renew-by-domain.
- `beacon_order_register(order_id, email, domain, webhook_secret)` - **OBSOLETE.** Kept only so old plugin versions don't error; idempotent. Nothing calls it.

Server-to-server (not MCP tools):
- `POST /api/v1/beacon/certificate_issued` - receives Beacon's issuance push, verifies the shared `BEACON_NOTIFY_SECRET` HMAC, enqueues `BeaconHandoffJob`. Primary handoff path (`Api::V1::BeaconController`).
- `Beacon::Client` (`app/services/beacon/client.rb`) - Rails → Beacon REST proxy used by the `cert_*` tools. Auth = Beacon's MCP_TOKEN, carried as `ENV["BEACON_PLUGIN_TOKEN_PUBLIC"]`; base URL `ENV["BEACON_BASE_URL"]` (default `https://beacon.tlsradar.com`).

Authenticated (Claude Code's built-in OAuth via `/mcp`):
- `me()` - plan tier, limits, usage
- `monitor_list()`, `monitor_add(domain)`, `monitor_add_bulk(domains[])`, `monitor_remove(domain|host_id)`
- `expiring(within?)` - cert-expiry view across user's hosts
- `scan_history(domain, limit?)` - recent ScanResults for one host
- `export()` / `import(payload)` - JSON workspace dump/restore
- `team_invite(email, team_id?, role?)`

### Beacon tools (now internal - reached only via the `cert_*` proxy)

The plugin no longer connects to `beacon.tlsradar.com/mcp` directly. `Beacon::Client` calls Beacon's REST API (`POST {base}/api/<tool>`, same registry as `/mcp`) server-to-server. The Beacon tool names the proxy depends on: `create_order`, `check_propagation`, `finalize_order`, `get_order_status` (NOT `order_status`), `renew_order` (NOT `renew`), `issue_with_csr`, `issue_certificate` (NOT `issue`), `list_order_events`. If you add/rename a Beacon tool, update `Beacon::Client` and the `cert_*` tools - and verify against the live Beacon `tools/list`. (Beacon's public `/mcp` stays up for backward-compat with old plugin installs and direct API users; the plugin just doesn't use it.)

### Environment variables

Plugin (user shell, interpolated by `.mcp.json` as `${VAR}` / `${VAR:-default}`):
- `TLSRADAR_BASE_URL` - override the one MCP server URL for staging/self-host. Default `https://tlsradar.com`.
- `TLSRADAR_INSTALL_ID` - optional anonymous funnel-attribution id (the hook mints one at `~/.config/tlsradar/install_id`; export it to activate). Sent as the `X-TLSRadar-Install` header; the MCP controller records it on `plugin_scan` / `plugin_cert_create` analytics. Unset = no-op. **There is no longer any `BEACON_PLUGIN_TOKEN` / `BEACON_BASE_URL` in the plugin** - those moved server-side to Rails.

Rails (server): `BEACON_PLUGIN_TOKEN_PUBLIC` (Beacon MCP token for the proxy), `BEACON_BASE_URL` (default `https://beacon.tlsradar.com`), `BEACON_NOTIFY_SECRET` (verifies the issuance push; = Beacon's `TLSRADAR_NOTIFY_SECRET`).

## How to add a slash command

1. Create `commands/tls-<verb>.md` with YAML frontmatter:
   ```yaml
   ---
   description: One-line summary that appears in `/` autocomplete
   argument-hint: "[positional args]"            # optional
   allowed-tools: Bash(open*)                     # optional, narrow
   ---
   ```
2. Body is a system prompt to Claude. Tell it exactly which MCP tool to call and how to render the result. Reference tools by `tlsradar.<name>` or `beacon.<name>` - Claude resolves the namespacing.
3. If the command has a funnel touchpoint (monitor cap, signup nudge, upgrade prompt), say "lead with X, mention Y in one closing line" so the model doesn't choice-paralysis the user.
4. Update `skills/certificate-monitoring/SKILL.md`'s "Choosing the right tool" table.
5. Update this CLAUDE.md's funnel diagram if the command sits on the path.
6. Update `README.md`'s quick-reference if the command is user-discoverable.

## How to extend the skill

There's one skill: `skills/certificate-monitoring/SKILL.md`. It's the natural-language router - when the user says "is my cert expiring," Claude reads this and picks `tlsradar.expiring`.

When you add a new MCP tool to TLS Radar's backend, add a row to the skill's "Choosing the right tool" table. The skill also documents two cross-cutting behaviors:

1. **401 auto-handling.** Any authenticated tool returning "unauthorized" → skill instructs Claude to surface `/mcp` instructions, not propagate the error.
2. **Funnel etiquette.** Lead with the recommended_upgrade from `LimitReachedPayload`; mention `also_available` in one closing line; offer `/tls-upgrade` for explicit browsing.

Both are written so a model reading the skill mid-conversation chooses the right behavior without re-deriving it.

## The hook

`hooks/hooks.json` runs once at SessionStart when `~/.config/tlsradar/welcomed.rev1` doesn't exist. It:
1. Mints the anonymous `~/.config/tlsradar/install_id` if absent.
2. **Activates funnel attribution by default** - idempotently appends `export TLSRADAR_INSTALL_ID=<id>` (behind a `# tlsradar-install-id` marker) to the user's shell rc (`~/.zshrc` / `~/.bashrc` / `~/.profile`, chosen from `$SHELL`). From the next shell on, `.mcp.json` interpolates the id into the `X-TLSRadar-Install` header with no user action. The welcome discloses this and tells the user to delete that line to opt out. (`.mcp.json` only does env interpolation, so the rc export is the only way to make attribution on-by-default; the previous "export it yourself to activate" left ~all installs unattributed.)
3. Migrates old v0.1.0 credentials (the deleted Go binary stored them at the same path), then touches the flag file.

**Welcome flag is decoupled from the plugin version (deliberate - item #5).** The flag is `welcomed.revN`, NOT `welcomed.v<semver>`. Bump `revN` (→ `welcomed.rev2`, and the matcher + `touch` in `hooks.json`) ONLY when a release materially changes how users interact - so routine semver bumps (bugfixes, backend-only changes) don't re-show the welcome and train users to dismiss it. The plugin version in the welcome *text* can track semver freely; only the *flag* is rev-gated.

## Release process

1. Verify locally: `.mcp.json` interpolates correctly; all `tlsradar.*` names match production `tools/list`. Run `python3 scripts/verify_tool_names.py` and `python3 evals/run_evals.py` (CI runs both, offline/deterministic). For the Beacon side, run `python3 scripts/verify_beacon_contract.py` (needs `BEACON_PLUGIN_TOKEN_PUBLIC`) - it calls Beacon's live `tools/list` and asserts every name in the manifest's `beacon` section still exists, so the `cert_*` proxy dependency can't silently drift. CI runs it too, but as a **non-blocking** job (it needs the network + token; an inconclusive run is ignored, only real drift is surfaced). If a tool was renamed/added, update `tools/manifest.json` (and the `Beacon::Client` + `cert_*` tools on the Rails side for beacon renames) in the same PR.
2. Bump `.claude-plugin/plugin.json` version (semver). Update the plugin version shown in the welcome *text*. Only bump the `welcomed.revN` flag in `hooks/hooks.json` (matcher + `touch`) if this release materially changes how users interact - otherwise leave it so the welcome doesn't re-show on routine releases.
3. Update README's `## How it works` if the architecture changed.
4. Update this CLAUDE.md's `## Repo layout` if files moved.
5. Tag and push: `git tag v0.X.0 && git push --tags`.
6. (Future) Submit to whatever Claude Code marketplace becomes the install path.

## Known issues / future work

- **Beacon docs vs reality.** Beacon's README claims `/mcp` auth is "optional." Production deploys it with `MCP_TOKEN` set, so it's mandatory in practice. If you build against a freshly cloned local Beacon and forget the token, your code will silently take Path A; in production it'll all fall to Path B (web form). Always verify against production.
- **Behavior is still only loosely tested.** `scripts/verify_tool_names.py` now guards against bad *tool names* (the one failure that has actually bitten us), but the rest is Markdown - there's no way to unit-test the model's behavior. Behavior is verified against the live MCP endpoint as part of the deploy flow on the TLS Radar app side. If you change something risky, run a real `/tls-cert` against a `dcv-inspector.com` test slot before merging.
- **Single skill.** Could grow into multiple (cert-monitoring, cert-issuance, billing) if the command set keeps expanding. For now, the rule of thumb is: if Claude is choosing between two tools that solve different problems, the skill is fine. If Claude is confused about WHAT problem the user has, split the skill.

### Backend reliability work - DONE (implemented across both repos)

These spanned the [tls_radar](https://github.com/TLS-Radar/tls_radar) (Rails) and [beacon](https://github.com/TLS-Radar/beacon) (Go) repos and have shipped:

1. **Funnel no longer depends on the client-side register step.** Beacon's issuance notifier (`internal/tlsradar/notify.go`) now fires for any plugin-originated order - one whose `webhook_url` targets the TLS Radar host (`targetsTLSRadar`), not just marketing-consent orders - and pushes the `email` + `domain` it already holds to TLS Radar's new `POST /api/v1/beacon/certificate_issued` (`Api::V1::BeaconController`, shared-secret HMAC), which runs `BeaconHandoffJob`. `tlsradar.beacon_order_register` is now obsolete; the plugin doesn't call it. Config: Beacon's `TLSRADAR_NOTIFY_URL`/`TLSRADAR_NOTIFY_SECRET` (already deployed) must pair with TLS Radar's `BEACON_NOTIFY_SECRET` (added to `config/deploy.yml`).
2. **Composite issuance tool.** Beacon's `finalize_order` runs validate → wait-for-LE → issue server-side in one call (`internal/web/api_tools.go`), bounded by `max_wait_seconds` (≤75s, under the 90s write timeout). The plugin's `/tls-cert` now collects the domain, surfaces DNS records, and makes one `finalize_order` call instead of conducting validate→poll→issue.
3. **Single MCP server (proxy).** The plugin points only at `tlsradar.com/api/v1/mcp`. Public `cert_*` tools (`app/services/mcp_services/tools/cert_*.rb`) proxy Beacon's REST API via `Beacon::Client` server-to-server. The `.mcp.json` dropped the second server and the `BEACON_PLUGIN_TOKEN` entirely - one connection, one auth model, no fallback "Path B." Beacon's public `/mcp` stays up for back-compat but the plugin doesn't use it.
4. **One reliable handoff channel.** `cert_create` persists the `BeaconOrder` mapping at creation (email known server-side from the start) and the completion push is the sole handoff trigger; the proxy doesn't store the per-order webhook secret, so `/webhooks/beacon` can't double-fire it.
5. **CSR-only issuance.** `/tls-cert` generates the key + CSR locally with `openssl` and sends only the CSR (private key never leaves the machine, no passphrase in chat). Optional `.p12` is packaged locally too. The Beacon `passphrase` path still exists but the plugin doesn't use it.
6. **Thin plugin / rich tools / fewer commands.** Funnel guidance moved into the MCP tool `description` fields (e.g. `monitor_add`); the eight thin 1:1 command files were deleted (skill routes them via NL); only six commands remain.
7. **Tool-routing evals + anonymous install id.** `evals/` checks the model picks the *right* tool (not just that names exist); the hook mints `~/.config/tlsradar/install_id` and the `X-TLSRadar-Install` header feeds `plugin_scan`/`plugin_cert_create` analytics.

### Round 3 - challenge methods, async-ish issuance, projection, generated router (shipped)

8. **HTTP-01 + DNS-01 (manual & provider).** Beacon now supports `challenge=http-01` (apex only - the www host can't serve the file) alongside dns-01: `internal/acme` gained `GetHTTP01Challenges`/type-aware `AcceptChallenges`, the store persists `challenge_type`, `CheckPropagation` does an HTTP fetch for http-01, and `ValidateCSRForSANs` enforces the right SAN set per type. The plugin's `/tls-cert` lets the user pick `dns-01` (manual TXT), `dns-01-cloudflare`/`dns-01-route53` (Claude sets the TXT via the provider API using the user's **local** env token - Beacon never sees provider creds), or `http-01`, and saves the choice in `~/.config/tlsradar/config.json` (`default_challenge` + `per_domain`).
9. **Bounded, idempotent issuance (the async fix without a goroutine rewrite).** `finalize_order` caps its wait at ~25s (no 85s worker hold) and stores the issued chain (`orders.cert_chain`); the `csr_pem` path is **idempotent** - a completed order returns the stored chain via `IssueWithCSR`/`get_order_status.fullchain_pem`, so a timed-out proxy retry never re-issues against the LE quota. (Chose this over a background-goroutine rewrite of the cert path: lower risk, addresses the worker-hold + retry-safety concerns.)
10. **BeaconOrder is an explicit projection.** `app/models/beacon_order.rb` documents that Beacon is the system of record; `purge_stale!`/`stale_unprocessed` reclaim orphaned unprocessed rows past Beacon's 24h TTL (processed rows are kept as the idempotency record).
11. **Generated router, manifest as source of truth.** `tools/manifest.json` is the one place tool names live; the guard and evals derive their allowlist from it, and `scripts/generate_router.py` regenerates SKILL.md's tool table (CI `--check`). The eval-caught "missing `monitor_remove` row" class of drift is now structurally impossible.
12. **HTTP-01 pebble e2e.** `TestPebbleHTTP01Loop` exercises create(http-01)→challtestsrv→finalize(CSR)→idempotent-retry against a live pebble (skips without `PEBBLE_URL`).

### Round 4 - attribution on by default, funnel-as-data, graceful degradation, live contract check (shipped)

13. **Funnel attribution is on by default (#1).** The SessionStart hook now idempotently appends `export TLSRADAR_INSTALL_ID=<id>` (behind a `# tlsradar-install-id` marker) to the user's shell rc, so `.mcp.json`'s `X-TLSRadar-Install` header is populated from the next shell on with zero user action. Previously the id was minted but required a manual `export`, so ~all installs were unattributed. Welcome discloses it; delete the line to opt out.
14. **Welcome flag decoupled from semver (#5).** Flag is `welcomed.revN`, not `welcomed.v<semver>`. Routine releases no longer re-show the welcome - bump `revN` only on material interaction changes. See "The hook".
15. **Funnel behavior moved from prose to server data (#2).** `BillingServices::UpgradeNudge` computes the upgrade-nudge decision server-side (at-cap / expiring-volume thresholds, only when a higher tier exists) and `monitor_list`/`expiring` return it as `structuredContent.nudge`; `cert_finalize` returns `structuredContent.handoff`. The skill's old prose thresholds ("3+ expiring", "1/1 used") are gone - it now just surfaces the `nudge`/`handoff` fields when present. `LimitReachedPayload#upgrade_path` is the shared tier source (parameterized `utm_content` so nudges attribute separately). Tested in `upgrade_nudge_spec.rb`.
16. **Graceful degradation when Beacon is down (#4).** `Beacon::Client::Unavailable < Error` is raised on connection/timeout, 5xx, and not-configured (4xx stays a plain `Error`). The `cert_*` tools rescue `Unavailable` → `beacon_unavailable_result` (a friendly "briefly unavailable, scanning still works" message with `structuredContent.degraded/retryable`), so a Beacon blip at the funnel's value moment doesn't read as the plugin being broken. `/tls-cert`, `/tls-diagnose`, and the skill handle the `degraded` flag. Tested in `client_spec.rb` + `cert_tools_spec.rb`.
17. **Live Beacon contract check (#3).** `scripts/verify_beacon_contract.py` calls Beacon's live `tools/list` and asserts every name in the manifest's `beacon` section still exists - makes the "a human remembers to check tools/list" step executable. Runs as a **non-blocking** CI job (`beacon-contract`, `continue-on-error`) because it needs the network + a token; only real drift (exit 1) is worth attention, inconclusive (exit 2) is ignored.

### Round 5 - contract-as-artifact, resume tokens, provider helper, accretion cleanup (shipped)

18. **Cross-repo contract is now a generated artifact (#1).** Beacon commits its OpenAPI as a test-enforced snapshot (`internal/web/openapi.json`, kept fresh by `TestOpenAPISnapshot`). TLS Radar vendors it (`lib/beacon/openapi.json`) and **generates** `app/services/beacon/contract.rb` from it (`script/generate_beacon_client.rb`, `--check` in a spec). `Beacon::Client::DEPENDS_ON` (the fields the proxy reads) is asserted ⊆ the generated contract, so a Beacon field rename (e.g. `content`→`body`) fails CI instead of breaking issuance at runtime. The plugin's `verify_beacon_contract.py` now also checks those fields against Beacon's live `/openapi.json` (not just names). Field set mirrored in `tools/manifest.json` `beacon.*.fields`.
19. **Resume tokens decouple finishing an order from the 24h store TTL (#3).** `create_order` returns a signed, self-contained `resume_token` (`beacon/internal/orders/resume.go`); `finalize_order` accepts it and rehydrates a purged order's row before finalizing. Threaded through the proxy (`cert_create`→`cert_finalize`) and `/tls-cert` (saved with the order_id, passed at finalize). Forgery-proof (HMAC) and safe (rehydration still re-validates against LE). Needs `RESUME_TOKEN_SECRET` set on Beacon; empty disables.
20. **DNS-provider automation is tested code, not prose (#2).** `scripts/dns_provider.py` (+ `dns_provider_test.py`) owns the gotcha-prone logic - registrable-root extraction, the Cloudflare payload, Route 53's mandatory TXT double-quoting - as unit-tested pure functions. `/tls-cert` calls `dns_provider.py set|delete` instead of hand-built `curl`/`aws` in the prompt. Provider creds stay local (read from env by the helper).
21. **Server-minted install id + `client_id` arg (#4).** `resolve_install_id` (in `McpServices::Tool`) resolves the funnel id in order: sanitized header → `client_id` arg (lets the plugin pass its local id with NO shell export - closes the env-timing gap of Round 4 #13) → freshly minted. `scan`/`cert_create` echo the effective `install_id` so the plugin can persist a minted one. Format (`/\A[0-9a-f]{32}\z/`) enforced at the header boundary AND on the arg - the id flows into analytics distinct_ids, so attacker garbage is rejected (#6).
22. **Accretion cleanup (#5).** `store.Challenge`'s misleadingly-named `RecordName`/`RecordValue` Go fields are now neutral `Name`/`Value` (JSON was already `name`/`value`), with a doc comment that their meaning follows `Order.ChallengeType`. The redundant per-order webhook handoff enqueue is removed - `Webhooks::BeaconController` only projects `latest_state` now; the signed `certificate_issued` push is the genuinely sole handoff channel (dead `HANDOFF_STATES` const deleted).

### Still open / future work

- **Issuance is unauthenticated by design - not gated.** `cert_*` is public so anonymous users can issue (the funnel). We deliberately do NOT hard-gate on the install-id: it's a client-set header, trivially forged, so gating on it would be security theater that also dents conversion. Abuse control stays where it can't be faked: Beacon's per-IP rate limiter (`internal/ratelimit`) and Rails-layer throttling. If issuance abuse becomes real, add a proof-of-work or account requirement, not an install-id gate.
- **Add a `beacon.health` tool.** `/tls-diagnose` infers Beacon reachability from a `cert_status` probe (now reading the `degraded` flag). A dedicated health/ping tool would still be cleaner.
- **Funnel instrumentation is partial.** Install-id activation is now on by default (Round 4 #13), but signup attribution still isn't joined up end-to-end (install-id → signup → subscription).
- **`--llm` eval is opt-in.** Static coverage runs in CI; the model-routing check needs `ANTHROPIC_API_KEY`.
- **Beacon orders TTL vs renew.** Beacon purges orders ~24h after creation, so `cert_renew(order_id)` rarely applies at real renewal time; `/tls-renew` falls back to `cert_create`. (Resume tokens, Round 5 #19, now let a *single* in-flight order be finalized past the purge, but renew-by-domain still needs durable history.)
- **HTTP-01 needs port 80 reachable** by Let's Encrypt and is apex-only - document this to users; dns-01 remains the default for good reason.
- **Resume token edge case.** `EnsureFromResumeToken` rehydrates as `dns_pending`, so `finalize_order` re-runs `Validate`→`AcceptChallenges`. The common resume path (order created, never validated, resumed) works. The rare path - order *validated* on LE but not finalized, then purged (>24h) and resumed - can fail because `Accept` on an already-valid authz errors; the user just re-publishes the challenge. Not worth brittle "already valid?" detection in `Validate` for how rarely it happens. Resume tokens also embed the contact email (signed, not encrypted) - don't log them.

## Reference: backend repos

- TLS Radar (Rails): https://github.com/TLS-Radar/tls_radar
- Beacon (Go): https://github.com/TLS-Radar/beacon - read `internal/web/api_tools.go` for the tool registry (incl. `finalize_order`), `internal/mcp/mcp.go` for the JSON-RPC dispatcher, `internal/webhooks/webhooks.go` for the per-order webhook payload, and `internal/tlsradar/notify.go` for the server-to-server issuance push that drives the handoff.
- The handoff receiver on the Rails side is `app/controllers/api/v1/beacon_controller.rb` (`certificate_issued`), routed at `POST /api/v1/beacon/certificate_issued`.

When a contract changes upstream (new tool, renamed field, different auth), update this CLAUDE.md AND the affected slash command Markdown in the same PR.

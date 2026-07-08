# Changelog

All notable changes to the TLS Radar Claude Code plugin are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/); the plugin
uses [semantic versioning](https://semver.org/). The authoritative version is in
[`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json).

## [0.7.0] - 2026-07-08

More of `/tls-cert` moves from prose into tested code, issuance becomes
resumable across sessions, and the model-routing eval now runs on a
schedule.

### Added
- **Tested cert helper** (`scripts/cert_helper.py` +
  `cert_helper_test.py`). The key/CSR generation that used to be a
  hand-built `openssl req` line in the prompt is now
  `cert_helper.py csr`: it validates the domain before anything runs,
  picks the SAN set the order expects (dns-01 = apex+www, http-01 =
  apex), writes the key `0600` in a `0700` dir, and backs up an
  existing key instead of clobbering it (the old key may be the only
  copy of one still deployed).
- **Issued chains are verified before being presented as usable.**
  The fullchain PEM is server-provided (untrusted); it's saved with
  the Write tool (no shell) and `cert_helper.py verify-chain` then
  parses the leaf with openssl and refuses (exit 2) unless its SANs
  cover the requested domain - a wrong or garbage chain is caught
  before the user installs it. On success it reports SANs, expiry,
  and days remaining.
- **Resumable issuance.** `/tls-cert` persists each order to
  `~/.config/tlsradar/orders/<domain>.json` (order_id, resume_token,
  challenge, email, challenge records) and offers to resume an
  in-flight order from a previous session instead of starting over.
  Once issued, the file is marked `completed_at` and becomes local
  history: `/tls-renew` reads it to reuse the saved email and
  challenge method (with confirmation) instead of re-asking.
- **Scheduled LLM routing eval** (`.github/workflows/llm-eval.yml`).
  The real model-routing eval (`evals/run_evals.py --llm`) now runs
  weekly (and on manual dispatch) instead of being local-only, so a
  routing regression is noticed within days. Skips cleanly when the
  `ANTHROPIC_API_KEY` secret is absent; never gates merges.

### Changed
- `/tls-cert` and `/tls-renew` call the cert helper instead of
  hand-building `openssl req`; `cert_helper_test.py` runs in CI
  alongside the DNS-provider tests.

## [0.6.1] - 2026-07-05

Close a shell-injection boundary in the DNS-provider flow (buildwithclaude
review follow-up).

### Changed
- **Untrusted challenge records never touch a shell.** Previously
  `/tls-cert` interpolated the MCP response's `record.name`/`record.value`
  directly into the `dns_provider.py` command line, so shell expansion of
  `$(...)`, backticks, or `;` could happen before Python could reject the
  value. Now `/tls-cert` writes the records to
  `~/.config/tlsradar/challenge-records.json` with the Write tool (no
  shell), and the helper reads them via `--records-file`, structurally
  validates each (`json.load` can't execute; non-string fields rejected),
  runs the existing `_acme-challenge`/base64url checks on every record,
  and only then performs the provider write or delete. Only the fixed file
  path and the user's own domain reach the shell.

### Added
- **End-to-end repro test** (`MainClosesShellBoundary`) proving a malicious
  TXT value (e.g. `$(rm -rf ~)`) returns exit 2 with the provider never
  called, plus structural-validation and shell-metacharacter cases.

## [0.6.0] - 2026-07-05

Client-side hardening from the buildwithclaude marketplace review, and
removal of the SessionStart welcome hook.

### Added
- **DNS challenge validation before any provider write.**
  `scripts/dns_provider.py` now requires `--domain` and refuses to write
  (or delete) any record that isn't the expected `_acme-challenge`
  record for that domain (apex or a subdomain of it), and rejects TXT
  values that aren't plausible dns-01 tokens. A buggy or compromised
  MCP response can no longer steer a Cloudflare/Route 53 write into an
  unrelated zone you control. `/tls-cert` passes `--domain`; new tests
  cover suffix-confusion, unrelated zones, and bad values.

### Changed
- **Remote MCP responses are treated as untrusted data.** The skill and
  commands no longer relay server-authored strings (`handoff.message`,
  `nudge.message`, degraded-backend messages, or raw error text) verbatim
  or act on them. `/tls-diagnose` now classifies an unexpected error in
  client-authored wording and surfaces only validated structured fields
  (e.g. `degraded`, a numeric HTTP status) instead of echoing the raw
  server message. User-facing wording is client-authored; only validated
  structured values (tier name, numeric price/counts) are surfaced, with
  a fallback to `/tls-upgrade` when a field is missing or unexpected. The
  funnel behavior stays the same, just bounded by client-side rules.

### Removed
- **The SessionStart welcome hook** (the `hooks/` directory). It printed
  an onboarding banner and wrote a flag file on startup; a marketplace
  reviewer flagged the automatic home-directory write and startup promo.
  Attribution is unaffected - the install-id mint already lived in the
  scan/cert commands, and the config dir is created on demand.

## [0.5.1] - 2026-06-10

Docs-only patch for clean strict plugin validation.

### Changed
- **`commands/README.md` folded into `CONTRIBUTING.md` and removed.**
  `claude plugin validate --strict` parsed every flat `.md` under `commands/`
  as a slash command and flagged the dev-doc README for having no frontmatter.
  Moving it out of `commands/` clears that warning.
- **Refreshed stale doc lines to match 0.5.0:** the `.mcp.json` "install header"
  note, the hook "install-id mint" note, and the `commands/`/`skills/` tree
  labels in `CLAUDE.md` and `README.md`.

No runtime or behavior changes.

## [0.5.0] - 2026-06-10

Marketplace-readiness: anonymous attribution no longer touches your shell
config or sends a tracking header.

### Removed
- **Shell-config modification.** The plugin no longer appends anything to your
  `~/.zshrc` / `~/.bashrc` / `~/.profile`.
- **Default tracking header.** `.mcp.json` no longer sends an
  `X-TLSRadar-Install` header.
- **The risky SessionStart hook operations.** The welcome hook no longer runs
  `openssl`, the legacy `mv …/credentials.json` migration, or `rm` cleanups, and
  never touches your shell config. It now does only a `printf` welcome plus a
  one-time `touch` of a flag file in the plugin's own config dir (so it shows
  once, not every session). The install id is created by `/tls-scan` and
  `/tls-cert` from the server response, not the hook.

> **Upgrading from 0.4.0:** 0.4.0 added an `export TLSRADAR_INSTALL_ID=…` line
> (under a `# tlsradar-install-id` comment) to your shell rc. The new hook
> neither adds nor removes it - removing it would mean editing your shell
> config again, the very thing we stopped doing. The line is now harmless (the
> header that read it is gone), but you can delete those two lines yourself.

### Changed
- **Attribution now rides on a tool argument.** `/tls-scan` and `/tls-cert`
  read the install id from `~/.config/tlsradar/install_id` and pass it as a
  `client_id` argument - same anonymous, per-install signal, with no shell
  changes and no header. Opt out by deleting that file.
- **`/tls-cert` now states what your email is used for** when it's collected:
  the Let's Encrypt order and a one-time monitoring follow-up (marketing stays
  opt-in, default off).
- **Tighter `/tls-cert` permissions.** Dropped the blanket `Bash(aws*)` /
  `Bash(open*)` grants and scoped `python3` to the bundled DNS helper.

## [0.4.0]

The single-MCP-server, key-stays-local, funnel-attribution release.

### Changed
- **One MCP server.** The plugin points only at `tlsradar.com/api/v1/mcp`.
  Certificate issuance is proxied server-side to the Let's Encrypt backend
  (Beacon) - the second server and its token are gone. One connection, one auth
  model.
- **Welcome flag decoupled from the version** (`welcomed.revN`, not
  `welcomed.v<semver>`), so routine releases don't re-show the welcome.

### Added
- **Anonymous funnel attribution.** The SessionStart hook mints an install id
  at `~/.config/tlsradar/install_id`. (0.4.0 also exported it via a shell-rc
  line; that was removed in 0.5.0 - see above.)
- **HTTP-01 and DNS-01 challenges**, including provider automation
  (`dns-01-cloudflare`, `dns-01-route53`) via a tested local helper
  (`scripts/dns_provider.py`) that reads credentials from your local env only.
- **CSR-only issuance.** `/tls-cert` generates the key + CSR locally and sends
  only the CSR; the private key never leaves your machine. Optional `.p12` is
  packaged locally too.
- **Resume tokens** so an interrupted order can be finalized past the backend's
  24h order TTL.
- **Graceful degradation** when the cert backend is briefly unavailable - a
  friendly message instead of a hard error; scanning still works.
- **Tool-routing evals** and a generated SKILL.md router table, with
  `tools/manifest.json` as the single source of truth for tool names.
- Live Beacon contract check (`scripts/verify_beacon_contract.py`,
  non-blocking in CI).

### Security
- No tokens or credentials are shipped or committed; DNS-provider creds and
  certificate private keys stay local. See [`SECURITY.md`](./SECURITY.md).

## [0.3.0]
- Composite, bounded, idempotent issuance (`finalize_order`): validate →
  wait-for-LE → issue in one call, retry-safe so a timeout never re-issues.
- Thinner plugin: funnel guidance moved into MCP tool descriptions; the thin
  1:1 data commands were removed in favor of natural-language routing through
  the skill.

## [0.2.0]
- Server-to-server certificate → monitoring handoff via a signed
  `certificate_issued` push, replacing the client-side register step.

## [0.1.0]
- Initial release. (This version shipped a Go helper binary that stored
  credentials under `~/.config/tlsradar`; the SessionStart hook migrates that
  state forward and the binary is gone.)

[0.4.0]: https://github.com/TLS-Radar/tlsradar-claude-plugin

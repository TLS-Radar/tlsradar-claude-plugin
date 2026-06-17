# Changelog

All notable changes to the TLS Radar Claude Code plugin are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/); the plugin
uses [semantic versioning](https://semver.org/). The authoritative version is in
[`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json).

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

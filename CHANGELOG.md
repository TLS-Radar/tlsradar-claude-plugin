# Changelog

All notable changes to the TLS Radar Claude Code plugin are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/); the plugin
uses [semantic versioning](https://semver.org/). The authoritative version is in
[`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json).

## [0.4.0] - current

The single-MCP-server, key-stays-local, funnel-attribution release.

### Changed
- **One MCP server.** The plugin points only at `tlsradar.com/api/v1/mcp`.
  Certificate issuance is proxied server-side to the Let's Encrypt backend
  (Beacon) - the second server and its token are gone. One connection, one auth
  model.
- **Welcome flag decoupled from the version** (`welcomed.revN`, not
  `welcomed.v<semver>`), so routine releases don't re-show the welcome.

### Added
- **Anonymous funnel attribution, on by default.** The SessionStart hook mints
  an install id and appends an opt-out `export TLSRADAR_INSTALL_ID=…` line to
  your shell rc. Disclosed in the welcome; delete the line to opt out.
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

# Distribution & listing playbook

Where the TLS Radar plugin / MCP server is published, and how to keep coverage wide.
Status legend: **LIVE** · **PENDING** · **TODO (form)** · **TODO (PR)** · **AUTO** (indexes itself).

## Shared metadata (paste into any form)

- **Name:** TLS Radar
- **Plugin repo:** https://github.com/TLS-Radar/tlsradar-claude-plugin
- **MCP server URL:** https://tlsradar.com/api/v1/mcp  (Streamable HTTP; public `scan`/`cert_*` tools need no auth)
- **Homepage:** https://tlsradar.com/cli
- **Category / tags:** Security · ssl, tls, certificates, monitoring, letsencrypt, security
- **Short description (≤100 chars):** SSL/TLS scanning, free Let's Encrypt issuance, and certificate-expiry monitoring.
- **Long description:** Run SSL/TLS scans, issue free Let's Encrypt certificates (private key stays local), and monitor certificate expiry from inside Claude Code or Cowork — through a single MCP server, no account needed for scans and issuance.

## Anthropic channels (already handled)

- **Self-hosted marketplace** — **LIVE** — `/plugin marketplace add TLS-Radar/tlsradar-claude-plugin`
- **Community marketplace** (`anthropics/claude-plugins-community`) — **PENDING** review (submitted via claude.ai/settings/plugins/submit)
- **Official marketplace** (`claude-plugins-official`) — no application; Anthropic curates at its discretion.

## A. MCP server registries

The MCP server is usable by any MCP client (Cursor, Cline, Windsurf, VS Code, …), so list it independently of the plugin.

### 1. Official MCP Registry — TODO (CLI) — highest leverage
`server.json` is ready at the repo root. Publishing here **auto-propagates to downstream aggregators** (PulseMCP, Glama, and others pull from the official registry).

```bash
# 1. Install the publisher CLI (see https://modelcontextprotocol.io quickstart, e.g. `brew install mcp-publisher`)
# 2. Authenticate the namespace, then publish, from the repo root (where server.json lives):
mcp-publisher login dns --domain tlsradar.com   # add the printed TXT record (we own the domain)
mcp-publisher publish
```
- Namespace `com.tlsradar/tlsradar` requires **DNS** auth (fitting — we run DNS/TLS). See the registry Authentication guide for exact `login dns` flags.
- Simpler alternative: `mcp-publisher login github` (device flow). If you use this, change `name` in `server.json` to `io.github.TLS-Radar/tlsradar`.

### 2. mcp.so — TODO (form)
Submit at mcp.so (account). Paste the shared metadata + MCP URL.

### 3. smithery.ai — TODO (form)
Add server / connect GitHub; it's a remote server (Streamable HTTP URL above).

### 4. mcp.directory — TODO (form)
Submit at https://mcp.directory/submit with the shared metadata.

### 5. PulseMCP / Glama — AUTO
Both pull from the official registry; expect them to appear after step A.1. No separate action (can nudge via their submit form if slow).

### 6. punkpeye/awesome-mcp-servers — TODO (PR)
Add under the **Security** category, alphabetical, format `- [name](url) <scope emoji> - desc`:
```
- [TLS Radar](https://tlsradar.com/cli) ☁️ - SSL/TLS scanning, free Let's Encrypt issuance (private key stays local), and certificate-expiry monitoring over MCP.
```

## B. Claude plugin directories

### 1. claudemarketplaces.com — TODO (form / index)
Submit the plugin repo; uses the shared metadata. Many entries index public marketplaces automatically.

### 2. claudepluginhub.com — AUTO / TODO
Indexes Claude marketplaces; the plugin should appear once the community listing lands. Use their submit form if not picked up.

### 3. aitmpl.com/plugins — TODO (form/contact)
Submit/contact to be added to a collection.

### 4. hesreallyhim/awesome-claude-code — TODO (PR)
Add under the plugins/skills section:
```
- [TLS Radar](https://github.com/TLS-Radar/tlsradar-claude-plugin) - SSL/TLS scanning, free Let's Encrypt issuance, and certificate-expiry monitoring in Claude Code & Cowork.
```

### 5. rdmgator12/awesome-claude-plugins — AUTO
Tracks the official/community catalog; appears once the community listing lands.

## Launch moments (optional, after listings are live)

Product Hunt · Show HN · r/ClaudeAI, r/ClaudeCode, r/mcp · Anthropic (Claude Developers) Discord. Link all of them to https://tlsradar.com/cli.

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

### 1. Official MCP Registry — AUTOMATED (CI) — highest leverage
`.github/workflows/publish-mcp.yml` publishes `server.json` to the registry on every `vX.Y.Z` tag (which `release.yml` already creates on a version bump), keeping the registry version in lockstep with the release. Publishing here **auto-propagates to downstream aggregators** (PulseMCP, Glama, …), so this one workflow covers most of section A.

**One-time setup (DNS auth for the `com.tlsradar` namespace):**
1. Generate an Ed25519 key pair (see the registry [Authentication guide](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx)).
2. Publish the public key as a DNS **TXT record on `tlsradar.com`** (the host/value the guide prints).
3. Add the private key (hex) as the repo secret **`MCP_PRIVATE_KEY`** (Settings → Secrets and variables → Actions).

After that, every release publishes automatically. To publish on demand: run the workflow from the Actions tab (`workflow_dispatch`), or locally `mcp-publisher login dns --domain tlsradar.com && mcp-publisher publish` from the repo root.
- Namespace is `com.tlsradar/tlsradar` (DNS-verified — fitting, we run DNS/TLS). Switching to GitHub-OIDC auth instead would mean renaming to `io.github.TLS-Radar/tlsradar`.

### 2. mcp.so — TODO (form)
Submit at mcp.so (account). Paste the shared metadata + MCP URL.

### 3. smithery.ai — TODO (form)
Add server / connect GitHub; it's a remote server (Streamable HTTP URL above).

### 4. mcp.directory — TODO (form)
Submit at https://mcp.directory/submit with the shared metadata.

### 5. PulseMCP / Glama
- **PulseMCP** — AUTO: pulls from the official registry; expect it after the registry publish.
- **Glama** — TODO (submit + Dockerfile bridge): Glama scores servers by starting them in Docker and introspecting. TLS Radar is remote-hosted, so the repo ships a thin bridge [`Dockerfile`](../Dockerfile) (`mcp-remote` → `https://tlsradar.com/api/v1/mcp`) that starts and passes introspection — verified locally (17 tools listed). Submit at https://glama.ai/mcp/servers (provide the Dockerfile), and also list the hosted endpoint at https://glama.ai/mcp/connectors. Once Glama scores it, add the score badge to awesome-mcp-servers PR #8110.

### 6. punkpeye/awesome-mcp-servers — DONE (PR #8110)
Entry added under **Security** (alphabetical, `💎 ☁️`). Pending: add the Glama score badge after the description once Glama scores the server (see #5):
```
[![TLS-Radar/tlsradar-claude-plugin MCP server](https://glama.ai/mcp/servers/TLS-Radar/tlsradar-claude-plugin/badges/score.svg)](https://glama.ai/mcp/servers/TLS-Radar/tlsradar-claude-plugin)
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

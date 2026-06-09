# TLS Radar Claude Code Plugin

Run SSL/TLS scans, issue free Let's Encrypt certificates, and manage cert monitoring from inside Claude Code - through a single MCP server, with nothing to configure.

```
# Public - no account, no setup
/tls-scan example.com                       # free SSL/TLS scan
/tls-cert mydomain.dev                      # free 90-day Let's Encrypt cert (private key stays local)
/tls-renew mydomain.dev                     # renew a cert

# Connect once for monitoring (OAuth via /mcp)
/mcp                                        # built-in Claude Code OAuth flow
/tls-monitor add api.foo.io                 # one or many: /tls-monitor add a.com b.com c.com
/tls-monitor list
/tls-monitor remove api.foo.io
/tls-diagnose                               # health check (use when something's off)
/tls-upgrade                                # open pricing page
```

Other actions - "what's expiring soon," "scan history for X," "what plan am I on," "export/import my monitors," "invite a teammate" - just ask in plain language; the plugin's skill routes them to the right tool. No slash command needed.

## How it works

Claude Code's MCP client talks to **one** remote server:

- `tlsradar.com/api/v1/mcp`

Certificate issuance is **proxied through that server** to the Let's Encrypt backend (Beacon), so there's a single connection and a single auth model - no second server, no token to paste into your shell.

- **Public tools** (`scan`, `cert_create`, `cert_check_propagation`, `cert_finalize`, `cert_status`, `cert_renew`) work with no account.
- **Authenticated tools** (monitoring, plan info, export/import, team) use Claude Code's built-in OAuth 2.0 + PKCE. Run `/mcp` once, pick the `tlsradar` server, approve in the browser; the token is managed by Claude Code.

When you run `/mcp`, Claude Code fetches `tlsradar.com/.well-known/oauth-authorization-server` (RFC 8414), dynamically registers as a public client (RFC 7591), opens the browser for consent (PKCE / RFC 7636), and includes the token on subsequent requests automatically.

### Certificates keep your private key local

`/tls-cert` generates the key + CSR on **your** machine with `openssl` and sends only the CSR. The private key never leaves your computer and no passphrase is ever typed into the chat. If you want a `.p12` bundle (e.g. for Windows/Java import), the plugin packages it locally too.

You choose how to prove control of the domain, and the plugin remembers your choice (in `~/.config/tlsradar/config.json`):

- **`dns-01`** - you add a TXT record by hand (works anywhere).
- **`dns-01-cloudflare` / `dns-01-route53`** - the plugin sets the TXT record for you via the provider API, reading your token from the local environment (`CLOUDFLARE_API_TOKEN`, or your configured `aws` CLI). Those credentials stay on your machine - they're never sent to TLS Radar or Beacon.
- **`http-01`** - serve a file on `http://yourdomain` (port 80); issues the apex only.

When a cert is issued, TLS Radar emails you about ongoing monitoring - the cert → monitoring handoff is fully automatic and server-side.

## Install

In Claude Code, add the marketplace and install - two commands, no clone, no paths:

```
/plugin marketplace add TLS-Radar/tlsradar-claude-plugin
/plugin install tlsradar@tlsradar
```

(Or browse it in the `/plugin` menu after adding the marketplace.) That's it - scanning and cert issuance work immediately. Run `/mcp` when you want monitoring.

<details>
<summary>Manual install (no marketplace)</summary>

```bash
git clone https://github.com/TLS-Radar/tlsradar-claude-plugin ~/.claude/plugins/tlsradar
```
</details>

## Free plan limits

- **1 monitor** included free
- **1 alert per month**, delivered at 7 days before expiry
- Unlimited free scans (rate-limited)
- Free Let's Encrypt issuance
- REST API access on every plan, including Free

When you hit the monitor limit, the tool's response includes the recommended upgrade and a pricing URL.

## Configuration

Nothing is required. Optional environment variables:

- `TLSRADAR_BASE_URL` - override the TLS Radar URL (default `https://tlsradar.com`). Useful for staging/self-host.
- `TLSRADAR_INSTALL_ID` - anonymous funnel attribution id, **on by default**. On first run the SessionStart hook mints a random id at `~/.config/tlsradar/install_id` and appends an opt-out `export` line (behind a `# tlsradar-install-id` marker) to your shell rc (`~/.zshrc`, `~/.bashrc`, or `~/.profile`). From the next shell on, `.mcp.json` sends it as the `X-TLSRadar-Install` header so anonymous scan/cert usage can be attributed to one install. It identifies an install, not a person.

  **To opt out:** delete that line from your shell rc (and optionally `rm ~/.config/tlsradar/install_id`). With it unset, the server records nothing.

## Privacy & security

- This plugin ships **no tokens or credentials** - there's nothing secret in this repo. See [`SECURITY.md`](./SECURITY.md).
- The OAuth token is managed by Claude Code's MCP client, not by this plugin.
- Certificate private keys are generated locally and never sent to any server.
- DNS-provider credentials (`CLOUDFLARE_API_TOKEN`, AWS CLI) are read from your local environment and never sent to TLS Radar or Beacon.
- An anonymous install id is sent for funnel attribution (on by default - see Configuration above to opt out). It identifies an install, not a person.
- To revoke access: `https://tlsradar.com/oauth/authorized_applications` or remove the MCP server in `/mcp`.
- Access tokens expire in 2 hours; refresh tokens rotate on use, capped at 90 days.

## Layout

```
.
├── README.md                        # this file
├── CLAUDE.md                        # architecture / funnel / contracts (humans + AI agents)
├── CONTRIBUTING.md                  # dev loop + how to add commands
├── CHANGELOG.md                     # version history
├── SECURITY.md                      # reporting + why the plugin holds no secrets
├── LICENSE                          # MIT
├── .claude-plugin/plugin.json       # plugin manifest
├── .claude-plugin/marketplace.json  # self-hosting marketplace entry
├── .mcp.json                        # MCP server config (one remote URL)
├── commands/                        # slash commands (with their own README)
├── skills/                          # NL skill router (with its own README)
├── hooks/hooks.json                 # SessionStart welcome + install-id mint
├── tools/manifest.json              # single source of truth for tool names
├── scripts/                         # CI guards + tested DNS-provider helper
└── evals/                           # tool-routing evals (prompt → expected tool)
```

## Contributing

Start with [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the dev loop (all checks are offline and run with `python3`). For architecture, the funnel, contract pitfalls, and the release process, read [`CLAUDE.md`](./CLAUDE.md) - useful for both humans and AI agents. Changes are tracked in [`CHANGELOG.md`](./CHANGELOG.md).

Security reports: **security@tlsradar.com** (never a public issue) - see [`SECURITY.md`](./SECURITY.md).

## License

[MIT](./LICENSE) © TLS Radar

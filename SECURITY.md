# Security policy

## Reporting a vulnerability

Email **security@tlsradar.com** with the details. Please do not file public GitHub issues for security reports - open issues will be redirected and the original closed.

We aim to acknowledge within two business days. Significant fixes typically ship within a week; we'll keep you in the loop on timeline if anything takes longer.

## What's in scope for this repo

This plugin is pure configuration (Markdown + JSON). The relevant attack surfaces are:

- **Malicious slash command content** - if you find a command that could trick Claude into doing something harmful (deleting files, exfiltrating secrets, etc.), that's a vulnerability worth reporting.
- **`.mcp.json` exposing unintended endpoints** - if a misconfiguration could route the user's traffic to an attacker-controlled host, report it.
- **Hook script abuse** - `hooks/hooks.json` runs shell commands. If you find a way to inject untrusted input into one of those commands, report it.

## What's out of scope (file separately)

- TLS Radar backend (`tlsradar.com`) - report at `security@tlsradar.com` referencing the affected endpoint
- Beacon (`beacon.tlsradar.com`) - same address, mention "Beacon" in the subject
- Let's Encrypt or ACME protocol issues - those belong upstream

## This plugin holds no secrets

By design, the plugin ships nothing sensitive:

- **No API tokens or keys are committed.** Certificate issuance is proxied server-side through `tlsradar.com`, so there is no `BEACON_PLUGIN_TOKEN` (or any Beacon credential) in the plugin anymore - that moved to the Rails backend.
- **OAuth tokens** for authenticated tools are obtained and stored by Claude Code's built-in MCP client (`/mcp`), not by this plugin.
- **DNS-provider credentials** (`CLOUDFLARE_API_TOKEN`, AWS CLI config) are read from your **local** environment by `scripts/dns_provider.py` and are never sent to TLS Radar or Beacon.
- **Certificate private keys** are generated locally with `openssl` and never leave your machine.
- `TLSRADAR_INSTALL_ID` is an anonymous, non-secret attribution id minted on your machine; it identifies an install for funnel analytics, not a user.

## What we ask of researchers

- Don't access data that isn't yours during testing
- Don't run brute-force or scanning against the production endpoints
- A safe-harbor write-up after a fix is welcome; coordinate timing with us first

# Slash commands

Each `tls-*.md` file is a Claude Code slash command. When the user types `/tls-foo`, Claude reads the file's body as a system prompt and executes against it.

Read `../CLAUDE.md` first if you're new here - this file is a quick reference only.

## File format

```markdown
---
description: One-line summary (shows in `/` autocomplete)
argument-hint: "<required-arg>"   # optional
allowed-tools: Bash(open*)        # optional, narrows the auto-permission grant
---

System prompt body. Tell Claude:
- Which MCP tool to call (e.g., `tlsradar.monitor_add`)
- What arguments to pass and how to derive them from `$ARGUMENTS`
- How to render the result (table, summary, structured)
- What error cases to handle (and how)
- What NOT to do (anti-patterns specific to this command)
```

There are only six commands - the common funnel/multi-step flows. Everything else (expiring, scan history, plan info, export/import, team invite) is reached by natural language through the skill, which routes to the tool. Don't add a thin 1:1 command for a single tool; add a row to the skill's table instead.

## Naming conventions

- `tls-<verb>` for everything user-invoked
- Verbs match the dominant MCP tool: `tls-monitor` wraps `monitor_*`, `tls-cert` wraps the `cert_*` issuance tools, etc.
- Avoid abbreviations users wouldn't guess (`tls-mon` ✗, `tls-monitor` ✓)

## Tool names

The plugin talks to ONE server (`tlsradar`). Certificate issuance goes through `tlsradar.cert_create` → `tlsradar.cert_check_propagation` → `tlsradar.cert_finalize` (those proxy Beacon server-side). All tool names use the obvious form: `tlsradar.scan`, `tlsradar.monitor_add`, `tlsradar.cert_*`, etc.

`scripts/verify_tool_names.py` checks every `tlsradar.<name>` reference against the real registry on every PR - so a typo'd name fails CI. When adding a command, grep the TLS Radar repo's `app/services/mcp_services/tools/*.rb` for `NAME = ` to confirm names, and add new ones to the guard's `VALID` allowlist.

(Beacon's own tool names - `get_order_status` not `order_status`, `renew_order` not `renew` - only matter on the Rails proxy side now, in `Beacon::Client` + the `cert_*` tools. The plugin never names them.)

## 401 handling (don't duplicate)

The skill (`../skills/certificate-monitoring/SKILL.md`) already tells Claude: "if an authenticated tool returns 401, surface `/mcp` instructions, don't propagate the error." Don't restate that in every command - it gets ignored when stated everywhere and effective when stated once.

## Funnel etiquette (now lives in the tool description)

The "lead with `recommended_upgrade`, mention `also_available` in one closing line" guidance is baked into the `monitor_add` tool's `description` on the server, so the model gets it at call time without every command (or the skill) restating it. Don't re-encode it in command Markdown.

## Public vs authenticated commands

| Public (works without `/mcp` login) | Authenticated |
|---|---|
| `/tls-scan` | `/tls-monitor` |
| `/tls-cert` (public `cert_*` tools) | |
| `/tls-renew` (public `cert_*` tools) | |
| `/tls-upgrade` (just opens URL) | |
| `/tls-diagnose` (mix; calls public + tests auth) | |

`/tls-monitor` is the only authenticated command; it (and the NL-routed authed tools like `expiring`/`export`) rely on the skill's single 401-handling instruction.

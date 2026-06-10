# Contributing to the TLS Radar Claude Code plugin

Thanks for your interest. This plugin is **pure configuration + Markdown** - there is no binary to build. It's a set of slash commands, one natural-language skill, hooks, and a single `.mcp.json` pointing Claude Code at the TLS Radar MCP server.

If you're an AI agent working in this repo, read [`CLAUDE.md`](./CLAUDE.md) first - it's the fastest path to context (architecture, the conversion funnel, contract pitfalls, release process). Human contributors benefit from it too.

## Quick start

```bash
git clone https://github.com/TLS-Radar/tlsradar-claude-plugin
cd tlsradar-claude-plugin

# Everything below is offline and deterministic - no network, no tokens.
python3 scripts/verify_tool_names.py     # every tool reference resolves to the manifest
python3 evals/run_evals.py               # tool-routing evals (static check)
python3 scripts/generate_router.py --check  # SKILL.md table matches the manifest
python3 scripts/dns_provider_test.py     # DNS-provider helper unit tests
```

CI (`.github/workflows/verify-contracts.yml`) runs all four on every PR. Run them locally before opening one.

## Repository map

| Path | What it is |
|---|---|
| `.mcp.json` | The single MCP server config (one remote URL; no headers or tokens). |
| `commands/*.md` | Slash commands. Each is a system prompt telling Claude which MCP tool to call and how to render the result. |
| `skills/certificate-monitoring/SKILL.md` | The natural-language router - picks the right tool when there's no slash command. Its tool table is **generated** from the manifest. |
| `hooks/hooks.json` | One-time SessionStart welcome (print only; touches no shell config). The anonymous install id is created by the scan/cert commands, not the hook. |
| `tools/manifest.json` | **Single source of truth** for tool names (and the Beacon response fields the proxy reads). |
| `scripts/` | CI guards and the tested DNS-provider helper. |
| `evals/` | Prompt → expected-tool routing checks. |
| `CLAUDE.md` | Architecture, funnel, contracts, release process - read this. |

## How to add or change a slash command

Each `commands/tls-*.md` file is a slash command: when the user types `/tls-foo`, Claude reads the file body as a system prompt and executes against it.

1. Create `commands/tls-<verb>.md` with YAML frontmatter:
   ```markdown
   ---
   description: One-line summary (shows in `/` autocomplete)
   argument-hint: "<required-arg>"   # optional
   allowed-tools: Bash(open*)        # optional, narrows the auto-permission grant
   ---
   ```
2. The body is a system prompt to Claude. Tell it: which MCP tool to call (`tlsradar.<name>`) and how to derive args from `$ARGUMENTS`; how to render the result (table / summary / structured); what error cases to handle; and what NOT to do (command-specific anti-patterns).
3. If the command sits on the conversion funnel (cap hit, signup nudge, upgrade), state the desired framing ("lead with X, mention Y in one closing line").
4. Add a row to the skill's "Choosing the right tool" table (or regenerate it - see below).
5. Update `README.md`'s quick reference if the command is user-discoverable.

**Naming:** `tls-<verb>`, where the verb matches the dominant MCP tool (`tls-monitor` wraps `monitor_*`, `tls-cert` wraps the `cert_*` tools). Avoid abbreviations users wouldn't guess (`tls-mon` ✗).

**Keep the command set small.** There are only six commands - the common funnel/multi-step flows. Everything else (expiring, scan history, plan info, export/import, team invite) is reached by natural language through the skill. Don't add a thin 1:1 command for a single tool; add a row to the skill's table instead.

**Don't duplicate cross-cutting behavior.** 401 handling and funnel etiquette ("lead with `recommended_upgrade`…") each live in exactly one place - the skill, and the `monitor_add` tool `description` respectively. Restating them in every command makes the model tune them out. State once.

| Public (works without `/mcp` login) | Authenticated |
|---|---|
| `/tls-scan`, `/tls-cert`, `/tls-renew` (public tools) | `/tls-monitor` |
| `/tls-upgrade` (opens URL), `/tls-diagnose` (mix) | |

## Tool names are generated, not hand-maintained

`tools/manifest.json` is the one place tool names live. The CI guard and evals derive their allowlist from it, and `scripts/generate_router.py` regenerates the SKILL.md tool table:

```bash
python3 scripts/generate_router.py          # rewrite SKILL.md's table
python3 scripts/generate_router.py --check   # CI: fail if it's out of date
```

If you add or rename a tool on the backend, update the manifest in the same PR. Never edit the generated table by hand.

## Cross-repo contracts

This plugin depends on tool names and response fields exposed by two backends:

- **TLS Radar** (Rails): https://github.com/TLS-Radar/tls_radar
- **Beacon** (Go, the Let's Encrypt issuer, proxied server-side): https://github.com/TLS-Radar/beacon

`scripts/verify_beacon_contract.py` checks the live Beacon API against the manifest (needs network + a token, so it's non-blocking in CI). When a contract changes upstream, update `CLAUDE.md` **and** the affected command Markdown in the same PR.

## Style

- Keep commands thin. Funnel guidance increasingly lives in the MCP tool `description` fields, not in prose here.
- Don't hardcode tool names outside the manifest.
- Don't commit secrets. The plugin holds none by design (see [`SECURITY.md`](./SECURITY.md)); the `.gitignore` guards against stray credentials and certificate material.

## Reporting bugs / requesting features

Use the GitHub issue templates. Security issues go to **security@tlsradar.com**, never a public issue - see [`SECURITY.md`](./SECURITY.md).

## License

By contributing, you agree your contributions are licensed under the [MIT License](./LICENSE).

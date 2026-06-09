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
| `.mcp.json` | The single MCP server config (one remote URL + an anonymous install header). |
| `commands/*.md` | Slash commands. Each is a system prompt telling Claude which MCP tool to call and how to render the result. |
| `skills/certificate-monitoring/SKILL.md` | The natural-language router - picks the right tool when there's no slash command. Its tool table is **generated** from the manifest. |
| `hooks/hooks.json` | SessionStart welcome + one-time anonymous install-id mint. |
| `tools/manifest.json` | **Single source of truth** for tool names (and the Beacon response fields the proxy reads). |
| `scripts/` | CI guards and the tested DNS-provider helper. |
| `evals/` | Prompt → expected-tool routing checks. |
| `CLAUDE.md` | Architecture, funnel, contracts, release process - read this. |

## How to add or change a slash command

1. Create `commands/tls-<verb>.md` with YAML frontmatter (`description`, optional `argument-hint`, optional narrow `allowed-tools`).
2. The body is a system prompt to Claude. Reference tools as `tlsradar.<name>`.
3. If the command sits on the conversion funnel (cap hit, signup nudge, upgrade), state the desired framing ("lead with X, mention Y in one closing line").
4. Add a row to the skill's "Choosing the right tool" table (or regenerate it - see below).
5. Update `README.md`'s quick reference if the command is user-discoverable.

See [`commands/README.md`](./commands/README.md) for the full checklist.

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

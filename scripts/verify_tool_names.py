#!/usr/bin/env python3
"""Guard against hallucinated / stale MCP tool names in the plugin's prompts.

The plugin instructs Claude to call tools like `beacon.issue_certificate` and
`tlsradar.monitor_add` from plain Markdown. There is no compiler to catch a
typo, and v0.1.0 shipped with wrong names (`beacon.issue`, `beacon.order_status`,
`beacon.renew`). This script extracts every `beacon.*` / `tlsradar.*` reference
from the files that actually *instruct* tool calls and asserts each one is a
real tool.

The allowlist below is the single source of truth in this repo. It must be
cross-checked against the live `tools/list` of both MCP servers on every
release (see CLAUDE.md "Release process"). This check is intentionally static
and network-free so it is deterministic in CI and offline.

Exit 0 if all references are valid, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "manifest.json"


def load_valid() -> dict[str, set[str]]:
    """Derive the allowlist from tools/manifest.json - the single source of
    truth. Keys starting with '_' are comments, not tools. Cross-check the
    manifest against production tools/list on release."""
    data = json.loads(MANIFEST.read_text())
    out: dict[str, set[str]] = {}
    for server, tools in data.items():
        if server.startswith("_"):
            continue
        out[server] = {name for name in tools if not name.startswith("_")}
    return out


VALID: dict[str, set[str]] = load_valid()

# Only files that actually instruct tool calls. READMEs and CLAUDE.md are meta
# docs and deliberately contain the wrong legacy names in a "wrong -> right"
# table, so they are excluded.
def target_files() -> list[Path]:
    files = sorted(ROOT.glob("commands/tls-*.md"))
    files += sorted(ROOT.glob("skills/**/SKILL.md"))
    return files


REF_RE = re.compile(r"(beacon|tlsradar)\.([a-z_]+)(\*?)")


def main() -> int:
    files = target_files()
    if not files:
        print("verify_tool_names: no target files found", file=sys.stderr)
        return 1

    errors: list[str] = []
    for f in files:
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            for m in REF_RE.finditer(line):
                server, method, star = m.group(1), m.group(2), m.group(3)
                # Hostname segment, e.g. beacon.tlsradar.com
                if server == "beacon" and method == "tlsradar":
                    continue
                # TLD, e.g. tlsradar.com
                if method == "com":
                    continue
                # Glob / truncated prose, e.g. tlsradar.monitor_*
                if star or method.endswith("_"):
                    continue
                if method not in VALID[server]:
                    rel = f.relative_to(ROOT)
                    errors.append(f"{rel}:{lineno}: unknown tool '{server}.{method}'")

    if errors:
        print("Invalid MCP tool references found:\n")
        for e in errors:
            print(f"  {e}")
        print(
            "\nEvery beacon.*/tlsradar.* reference must match a real tool.\n"
            "If the name is correct but new, add it to VALID in this script\n"
            "AFTER confirming it against the server's live tools/list."
        )
        return 1

    total = sum(len(v) for v in VALID.values())
    print(
        f"OK: all MCP tool references across {len(files)} files resolve to one "
        f"of {total} known tools."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate the skill's tool-routing table from tools/manifest.json.

The router table in SKILL.md used to be hand-maintained, so it could silently
drift from the real tools (an eval once caught a missing monitor_remove row).
This makes the manifest the source of truth: the table between the
`<!-- BEGIN generated tool table -->` / `<!-- END ... -->` markers is generated
from it. Run without args to rewrite the block; run with --check (CI) to fail
if it's stale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "manifest.json"
SKILL = ROOT / "skills" / "certificate-monitoring" / "SKILL.md"

BEGIN = "<!-- BEGIN generated tool table (scripts/generate_router.py) -->"
END = "<!-- END generated tool table -->"


def build_table() -> str:
    data = json.loads(MANIFEST.read_text())
    rows = ["| User intent | Tool |", "|---|---|"]
    for name, meta in data["tlsradar"].items():
        if name.startswith("_") or "router" not in meta:
            continue
        ref = f"`tlsradar.{name}`"
        if meta.get("command"):
            ref += f" (or `{meta['command']}`)"
        rows.append(f"| {meta['router']} | {ref} |")
    return "\n".join(rows)


def render_block() -> str:
    return f"{BEGIN}\n\n{build_table()}\n\n{END}"


def splice(text: str, block: str) -> str:
    if BEGIN not in text or END not in text:
        raise SystemExit(f"markers not found in {SKILL}; add {BEGIN} / {END} around the table")
    pre = text.split(BEGIN)[0]
    post = text.split(END, 1)[1]
    return pre + block + post


def main() -> int:
    check = "--check" in sys.argv[1:]
    text = SKILL.read_text()
    desired = splice(text, render_block())
    if check:
        if text != desired:
            print("SKILL.md router table is stale - run: python3 scripts/generate_router.py", file=sys.stderr)
            return 1
        print("OK: SKILL.md router table matches tools/manifest.json")
        return 0
    SKILL.write_text(desired)
    print(f"Wrote generated router table to {SKILL.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

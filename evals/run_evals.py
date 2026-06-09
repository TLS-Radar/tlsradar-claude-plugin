#!/usr/bin/env python3
"""Tool-routing evals for the TLS Radar plugin.

The tool-name guard (scripts/verify_tool_names.py) catches a command that
*names* a tool that doesn't exist. It cannot catch the failure that actually
hurts: the model picking the WRONG tool (or none) for a user's request. These
evals close that gap.

Two modes:

  Static (default, no network): assert every `expect`ed tool in cases.jsonl is
  a real tool (per the guard's allowlist) AND is referenced by the skill router
  (skills/certificate-monitoring/SKILL.md). This is a cheap, deterministic
  drift check that runs in CI - if a case expects a tool the skill never
  mentions, routing will silently fail, and this flags it.

  LLM (--llm, needs ANTHROPIC_API_KEY): actually send each prompt to a model
  with the real tool list + the skill as system prompt, and assert the tool it
  calls is in the case's `expect` set. This is the real router eval; run it
  locally or in a gated CI job.

Exit 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = Path(__file__).resolve().parent / "cases.jsonl"
SKILL = ROOT / "skills" / "certificate-monitoring" / "SKILL.md"

# Reuse the guard's allowlist as the source of truth for valid tool names.
sys.path.insert(0, str(ROOT / "scripts"))
from verify_tool_names import VALID  # noqa: E402

ALL_TOOLS = set().union(*VALID.values())

# Minimal name -> description map for the LLM mode. Kept short on purpose; the
# point is to exercise routing, not to mirror the server's full schemas.
TOOL_DESCS = {
    "scan": "Run a free anonymous SSL/TLS scan of a hostname. No account.",
    "cert_create": "Start issuing a free Let's Encrypt cert; returns DNS records to publish.",
    "cert_check_propagation": "Check whether a cert order's DNS TXT records have propagated.",
    "cert_finalize": "Validate, wait, and issue a cert order (pass a CSR). Final step.",
    "cert_status": "Return the current state of a cert order.",
    "cert_renew": "Clone an existing cert order by order_id into a fresh issuance.",
    "me": "Return the user's plan tier, limits, and usage.",
    "monitor_list": "List the domains the user is monitoring.",
    "monitor_add": "Add one domain to ongoing certificate monitoring.",
    "monitor_add_bulk": "Add many domains to monitoring in one call.",
    "monitor_remove": "Remove a domain from monitoring.",
    "expiring": "List the user's monitored certs expiring within N days.",
    "scan_history": "Return recent scan results for one monitored domain.",
    "export": "Export the user's monitors as JSON.",
    "import": "Restore monitors from a JSON payload.",
    "team_invite": "Invite someone to the user's team by email.",
}


def load_cases() -> list[dict]:
    cases = []
    for i, line in enumerate(CASES.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def static_check(cases: list[dict]) -> int:
    skill_text = SKILL.read_text()
    errors = []
    for c in cases:
        for tool in c["expect"]:
            if tool not in ALL_TOOLS:
                errors.append(f"case {c['prompt']!r}: expects unknown tool {tool!r}")
            # The skill should reference the tool (bare name or tlsradar.<name>).
            if not re.search(rf"\b{re.escape(tool)}\b", skill_text):
                errors.append(
                    f"case {c['prompt']!r}: expected tool {tool!r} is not referenced "
                    f"in SKILL.md - the router can't learn to pick it"
                )
    if errors:
        print("Static eval check FAILED:\n")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"Static eval check OK: {len(cases)} cases, all expected tools are real and routed in SKILL.md.")
    return 0


def llm_check(cases: list[dict]) -> int:
    try:
        import anthropic
    except ImportError:
        print("--llm requires the `anthropic` package: pip install anthropic", file=sys.stderr)
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("--llm requires ANTHROPIC_API_KEY in the environment", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()
    system = SKILL.read_text()
    tools = [
        {
            "name": name,
            "description": desc,
            "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}},
        }
        for name, desc in TOOL_DESCS.items()
    ]

    failures = 0
    for c in cases:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=system,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": c["prompt"]}],
        )
        picked = next((b.name for b in msg.content if b.type == "tool_use"), None)
        ok = picked in c["expect"]
        flag = "ok  " if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{flag}] {c['prompt'][:60]!r} -> {picked} (expected {c['expect']})")

    if failures:
        print(f"\nLLM eval: {failures}/{len(cases)} cases routed to the wrong tool.")
        return 1
    print(f"\nLLM eval OK: {len(cases)}/{len(cases)} cases routed correctly.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="run the real model-routing eval (needs ANTHROPIC_API_KEY)")
    args = ap.parse_args()

    cases = load_cases()
    rc = static_check(cases)
    if args.llm:
        rc = llm_check(cases) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

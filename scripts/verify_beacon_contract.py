#!/usr/bin/env python3
"""Live contract check: do the Beacon tool names the proxy depends on still exist?

The hazard this closes (CLAUDE.md flags it as the recurring break): tool names
live in THREE places - Beacon owns them (Go), the Rails `cert_*` proxy mirrors
them in `Beacon::Client` + the cert tools, and this plugin records the set it
depends on in `tools/manifest.json` under the `beacon` key. The offline guard
(`verify_tool_names.py`) only checks the *plugin's* refs are in the manifest; it
CANNOT notice when Beacon renames `order_status` -> `get_order_status` upstream.
That rename silently breaks issuance, and the only existing safeguard was "a
human remembers to check the live tools/list on release."

This script makes that check executable: it calls Beacon's live `tools/list`
(MCP JSON-RPC) and asserts every name in the manifest's `beacon` section is
present. It is intentionally SEPARATE from verify_tool_names.py because it needs
the network and is therefore non-deterministic - it must never gate offline CI.

Usage:
    python3 scripts/verify_beacon_contract.py [--base URL] [--token TOKEN]

  --base   Beacon base URL (default $BEACON_BASE_URL or https://beacon.tlsradar.com)
  --token  Bearer token if the deploy requires one
           (default $BEACON_PLUGIN_TOKEN_PUBLIC; prod has MCP_TOKEN set, so this
           is usually required - see CLAUDE.md "Beacon docs vs reality").

Exit codes:
    0  every manifest beacon tool exists upstream
    1  a manifest tool is missing upstream (real contract drift - fix it)
    2  couldn't reach Beacon / no token (inconclusive - DON'T treat as a failure
       in blocking CI; this is why the CI job is continue-on-error)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "manifest.json"
DEFAULT_BASE = "https://beacon.tlsradar.com"


def manifest_beacon_tools() -> set[str]:
    data = json.loads(MANIFEST.read_text())
    beacon = data.get("beacon", {})
    return {name for name in beacon if not name.startswith("_")}


def manifest_beacon_fields() -> dict[str, list[str]]:
    """Response fields the proxy depends on, per Beacon tool (mirrors
    Beacon::Client::DEPENDS_ON on the Rails side)."""
    data = json.loads(MANIFEST.read_text())
    out = {}
    for name, meta in data.get("beacon", {}).items():
        if name.startswith("_"):
            continue
        if isinstance(meta, dict) and meta.get("fields"):
            out[name] = meta["fields"]
    return out


def live_response_fields(base: str) -> dict[str, set[str]]:
    """Fetch Beacon's /openapi.json and return each operation's declared 200
    response field names. /openapi.json is public (no token needed)."""
    url = base.rstrip("/") + "/openapi.json"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        doc = json.loads(resp.read().decode())
    out: dict[str, set[str]] = {}
    for path, methods in doc.get("paths", {}).items():
        op = methods.get("post", {})
        name = op.get("operationId") or path.lstrip("/")
        schema = (
            op.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        out[name] = set((schema.get("properties") or {}).keys())
    return out


def live_beacon_tools(base: str, token: str | None) -> set[str]:
    """Call Beacon's MCP tools/list (JSON-RPC 2.0) and return the tool names."""
    url = base.rstrip("/") + "/mcp"
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    ).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())

    if "error" in payload:
        raise RuntimeError(f"Beacon tools/list returned an error: {payload['error']}")
    tools = payload.get("result", {}).get("tools", [])
    return {t["name"] for t in tools if "name" in t}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("BEACON_BASE_URL") or DEFAULT_BASE)
    parser.add_argument("--token", default=os.environ.get("BEACON_PLUGIN_TOKEN_PUBLIC"))
    args = parser.parse_args()

    expected = manifest_beacon_tools()
    if not expected:
        print("verify_beacon_contract: manifest has no beacon tools to check", file=sys.stderr)
        return 1

    try:
        live = live_beacon_tools(args.base, args.token)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as e:
        print(f"⚠ Inconclusive - couldn't query Beacon at {args.base}: {e}", file=sys.stderr)
        print("  (network/token issue, not contract drift; CI treats this as non-fatal)", file=sys.stderr)
        return 2

    missing = sorted(expected - live)
    if missing:
        print("✗ Beacon contract drift - the proxy depends on tools Beacon no longer exposes:\n")
        for name in missing:
            print(f"    beacon.{name}")
        print("\nThe manifest's `beacon` section is out of sync with Beacon's live tools/list.")
        print("Fix BOTH the Rails proxy (Beacon::Client + cert_* tools) AND tools/manifest.json,")
        print("then re-run. Live tools observed: " + ", ".join(sorted(live)))
        return 1

    # Field-level check: every response field the proxy reads must still be in
    # Beacon's published response schema (catches renames like content->body
    # that a names-only check misses). Uses the public /openapi.json.
    field_errors: list[str] = []
    try:
        live_fields = live_response_fields(args.base)
        for op, fields in manifest_beacon_fields().items():
            have = live_fields.get(op, set())
            for f in fields:
                if f not in have:
                    field_errors.append(f"    beacon.{op}.{f}  (response schema has: {', '.join(sorted(have)) or '<none>'})")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        print(f"⚠ Names verified, but couldn't field-check via /openapi.json: {e}", file=sys.stderr)
        return 2

    if field_errors:
        print("✗ Beacon FIELD drift - the proxy reads response fields Beacon no longer returns:\n")
        print("\n".join(field_errors))
        print("\nA field was renamed/removed upstream. Update Beacon::Client::DEPENDS_ON +")
        print("tools/manifest.json `fields`, re-vendor lib/beacon/openapi.json, regenerate.")
        return 1

    extra = sorted(live - expected)
    note = f" (Beacon also exposes, unused by the proxy: {', '.join(extra)})" if extra else ""
    print(f"✓ All {len(expected)} manifest beacon tools - and the response fields the proxy reads - exist on {args.base}{note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

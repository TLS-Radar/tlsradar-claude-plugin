#!/usr/bin/env python3
"""Print the CHANGELOG.md section for a given version, for release automation.

Usage:
    python3 scripts/extract_changelog.py 0.4.0

Prints everything under the `## [0.4.0] ...` heading up to (but not including)
the next `## [` heading. The heading line itself is omitted — the release title
already carries the version. Exit codes:

    0  section found and printed
    1  no section for that version (caller can fall back to --generate-notes)

Matching is tolerant of any suffix after the version bracket (e.g. a date or
"- current"), so `## [0.4.0] - 2026-06-09` and `## [0.4.0] - current` both match.
"""
import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def extract(text: str, version: str) -> str | None:
    # A version heading: "## [" + exact version + "]" + anything to end of line.
    start = re.compile(r"^##\s+\[" + re.escape(version) + r"\].*$", re.MULTILINE)
    m = start.search(text)
    if not m:
        return None
    rest = text[m.end():]
    # Stop at the next version heading ("## [").
    nxt = re.search(r"^##\s+\[", rest, re.MULTILINE)
    body = rest[: nxt.start()] if nxt else rest
    return body.strip("\n")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: extract_changelog.py <version>", file=sys.stderr)
        return 1
    version = argv[1].lstrip("v")
    section = extract(CHANGELOG.read_text(encoding="utf-8"), version)
    if not section:
        print(f"no changelog section for {version}", file=sys.stderr)
        return 1
    print(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

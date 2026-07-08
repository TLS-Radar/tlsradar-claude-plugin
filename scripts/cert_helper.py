#!/usr/bin/env python3
"""The deterministic, local half of /tls-cert: key+CSR generation and
verification of the issued chain.

Why this exists: like scripts/dns_provider.py, these steps used to live as
shell snippets inside a prompt - untested, and re-derived by the model on
every run. The gotcha-prone parts (the SAN set per challenge type, private-key
file permissions, checking that the PEM the server returned actually covers
the requested domain) are pure functions here, covered by
scripts/cert_helper_test.py. The openssl invocations are argv lists to
subprocess - nothing uses `shell=True`, so nothing is ever shell-expanded.

    cert_helper.py csr          --domain example.com --challenge dns-01
    cert_helper.py verify-chain --domain example.com --challenge dns-01 \
        --chain-file ~/.config/tlsradar/certs/example.com.fullchain.pem

`csr` validates the domain, generates an RSA key (0600, in a 0700 dir) plus a
CSR with the SAN set the order expects (dns-01 issues apex+www, http-01 the
apex only), and prints a JSON summary. An existing key/CSR is backed up, never
clobbered - the old key may be the only copy of one still deployed somewhere.

`verify-chain` treats the chain file as UNTRUSTED (it came from the remote MCP
response; the caller writes it to disk with a structured, non-shell tool and
passes only the fixed path here). It parses the leaf with `openssl x509` and
refuses (exit 2) unless the leaf's SANs cover the requested domain - so a
wrong or garbage chain is caught before the user installs it. On success it
reports the SANs and expiry as JSON.

Only the user's own domain and fixed local paths ever appear on the command
line; every server-provided byte travels via files.

Exit 0 on success; 1 on an openssl/environment failure; 2 when validation
rejects the input before anything is written or trusted.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys

DEFAULT_CERTS_DIR = os.path.join("~", ".config", "tlsradar", "certs")

# Hostname labels for a certificate domain: letters/digits/hyphen, no leading
# or trailing hyphen. (Stricter than dns_provider's label rule - underscores
# belong in _acme-challenge names, not in the domain a cert is issued for.)
_LABEL = re.compile(r"\A[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")


# --- pure helpers (tested) ---------------------------------------------------

def validate_domain(domain: str) -> str:
    """Normalize and validate the domain the user asked a cert for.

    Returns the lowercased, trailing-dot-stripped form. Raises ValueError on
    anything that isn't a plausible issuable hostname (wildcards included -
    this flow never issues them). This runs before any file or subprocess is
    touched, so a bad value can't reach openssl's -subj/-addext either.
    """
    dom = domain.strip().rstrip(".").lower()
    if not dom:
        raise ValueError("domain is empty")
    if "*" in dom:
        raise ValueError(f"wildcard domain {domain!r} is not supported by this flow")
    if len(dom) > 253:
        raise ValueError(f"domain {domain!r} is too long")
    labels = dom.split(".")
    if len(labels) < 2:
        raise ValueError(f"domain {domain!r} has no TLD - expected something like example.com")
    for lbl in labels:
        if not _LABEL.match(lbl):
            raise ValueError(f"domain {domain!r} has an invalid label {lbl!r}")
    return dom


def san_set(domain: str, challenge: str) -> list[str]:
    """The SAN set the Beacon order expects for this challenge type.

    Mirrors the server contract: dns-01 orders issue apex + www, http-01
    issues the apex only (the www host can't serve the challenge file). The
    CSR must match the order's SANs or finalize is rejected server-side.
    """
    if challenge == "http-01":
        return [domain]
    return [domain, f"www.{domain}"]


def openssl_req_args(domain: str, sans: list[str], key_path: str, csr_path: str) -> list[str]:
    """argv for the key+CSR generation - a list, never a shell string."""
    alt = ",".join(f"DNS:{s}" for s in sans)
    return [
        "openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
        "-keyout", key_path, "-out", csr_path,
        "-subj", f"/CN={domain}", "-addext", f"subjectAltName={alt}",
    ]


def count_pem_certs(text: str) -> int:
    return len(re.findall(r"-----BEGIN CERTIFICATE-----", text))


def parse_cert_text(text: str) -> dict:
    """Extract the SAN list and notAfter from `openssl x509 -noout -text` output.

    Pure parsing of untrusted-derived text: unknown/missing sections yield an
    empty SAN list or None rather than a crash, and the caller decides whether
    that's fatal.
    """
    sans: list[str] = []
    m = re.search(r"Subject Alternative Name:[^\n]*\n\s*([^\n]+)", text)
    if m:
        for entry in m.group(1).split(","):
            entry = entry.strip()
            if entry.startswith("DNS:"):
                sans.append(entry[len("DNS:"):].strip().rstrip(".").lower())
    nm = re.search(r"Not After\s*:\s*([^\n]+)", text)
    not_after = nm.group(1).strip() if nm else None
    return {"sans": sans, "not_after": not_after}


def covers_domain(sans: list[str], domain: str) -> bool:
    """True if the SAN list covers `domain` (exact or a matching wildcard)."""
    dom = domain.rstrip(".").lower()
    for san in sans:
        s = san.rstrip(".").lower()
        if s == dom:
            return True
        if s.startswith("*.") and "." in dom and dom.split(".", 1)[1] == s[2:]:
            return True
    return False


def days_remaining(not_after: str, now: _dt.datetime | None = None) -> int | None:
    """Days until `not_after` (an openssl date like 'Jul  5 12:00:00 2026 GMT').

    Returns None when the date doesn't parse - the caller reports the raw
    string instead of guessing.
    """
    s = re.sub(r"\s+", " ", not_after).strip()
    if s.endswith(" GMT") or s.endswith(" UTC"):
        s = s[:-4]
    try:
        dt = _dt.datetime.strptime(s, "%b %d %H:%M:%S %Y").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return (dt - now).days


# --- subcommands (thin wrappers) ---------------------------------------------

def _backup_existing(path: str) -> str | None:
    """Move an existing file aside instead of clobbering it.

    The existing key may be the only copy of one still deployed; renewal must
    never destroy it. Returns the backup path, or None if nothing existed.
    """
    if not os.path.exists(path):
        return None
    backup = f"{path}.{int(_dt.datetime.now(_dt.timezone.utc).timestamp())}.bak"
    os.replace(path, backup)
    return backup


def cmd_csr(args: argparse.Namespace) -> int:
    try:
        domain = validate_domain(args.domain)
    except ValueError as e:
        print(f"refusing CSR generation: {e}", file=sys.stderr)
        return 2

    certs_dir = os.path.expanduser(args.dir)
    os.makedirs(certs_dir, exist_ok=True)
    os.chmod(certs_dir, 0o700)  # the dir holds private keys

    key_path = os.path.join(certs_dir, f"{domain}.key")
    csr_path = os.path.join(certs_dir, f"{domain}.csr")
    backups = [b for b in (_backup_existing(key_path), _backup_existing(csr_path)) if b]

    sans = san_set(domain, args.challenge)
    old_umask = os.umask(0o077)  # key is 0600 from the moment it exists
    try:
        proc = subprocess.run(
            openssl_req_args(domain, sans, key_path, csr_path),
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("openssl is not installed or not on PATH", file=sys.stderr)
        return 1
    finally:
        os.umask(old_umask)
    if proc.returncode != 0:
        print(f"openssl req failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1
    os.chmod(key_path, 0o600)

    print(json.dumps({
        "domain": domain, "sans": sans,
        "key": key_path, "csr": csr_path,
        "backed_up": backups,
    }, indent=2))
    return 0


def cmd_verify_chain(args: argparse.Namespace) -> int:
    try:
        domain = validate_domain(args.domain)
    except ValueError as e:
        print(f"refusing verification: {e}", file=sys.stderr)
        return 2

    chain_path = os.path.expanduser(args.chain_file)
    try:
        with open(chain_path, "r", encoding="utf-8", errors="replace") as f:
            chain_text = f.read()
    except OSError as e:
        print(f"cannot read chain file: {e}", file=sys.stderr)
        return 1

    n_certs = count_pem_certs(chain_text)
    if n_certs < 1:
        print("chain file contains no PEM certificate - refusing it", file=sys.stderr)
        return 2

    # openssl x509 reads the FIRST cert in the file - the leaf in a
    # leaf-first fullchain, which is exactly the one that must cover the domain.
    try:
        proc = subprocess.run(
            ["openssl", "x509", "-noout", "-text", "-in", chain_path],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("openssl is not installed or not on PATH", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        print(f"chain file does not parse as a certificate: {proc.stderr.strip()}", file=sys.stderr)
        return 2

    parsed = parse_cert_text(proc.stdout)
    if not covers_domain(parsed["sans"], domain):
        print(
            f"issued certificate does NOT cover {domain} "
            f"(leaf SANs: {parsed['sans'] or 'none'}) - do not install it",
            file=sys.stderr,
        )
        return 2

    expected = set(san_set(domain, args.challenge))
    print(json.dumps({
        "domain": domain,
        "covers_domain": True,
        "sans": parsed["sans"],
        "missing_expected_sans": sorted(expected - set(parsed["sans"])),
        "not_after": parsed["not_after"],
        "days_remaining": days_remaining(parsed["not_after"]) if parsed["not_after"] else None,
        "certs_in_chain": n_certs,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    csr = sub.add_parser("csr", help="generate a local key (0600) + CSR with the order's SAN set")
    csr.add_argument("--domain", required=True, help="the domain the user requested the cert for")
    csr.add_argument("--challenge", required=True, choices=["dns-01", "http-01"],
                     help="dns-01 issues apex+www; http-01 the apex only - the CSR must match")
    csr.add_argument("--dir", default=DEFAULT_CERTS_DIR, help="where to write the key/CSR")
    csr.set_defaults(fn=cmd_csr)

    ver = sub.add_parser("verify-chain", help="verify the issued (untrusted) chain covers the domain")
    ver.add_argument("--domain", required=True, help="the domain the user requested the cert for")
    ver.add_argument("--challenge", required=True, choices=["dns-01", "http-01"])
    ver.add_argument("--chain-file", required=True,
                     help="path to the fullchain PEM the caller saved via a NON-shell tool")
    ver.set_defaults(fn=cmd_verify_chain)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

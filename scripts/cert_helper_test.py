#!/usr/bin/env python3
"""Tests for the pure logic in cert_helper.py, plus openssl round-trips.

The pure functions (domain validation, SAN sets, openssl argv construction,
chain-text parsing, domain coverage) are covered unconditionally. The two
end-to-end tests actually run openssl in a temp dir and are skipped when
openssl isn't installed (it is on macOS and the ubuntu CI runners).

Run: python3 scripts/cert_helper_test.py
"""

import contextlib
import datetime as dt
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert_helper as ch  # noqa: E402

HAVE_OPENSSL = shutil.which("openssl") is not None


class ValidateDomain(unittest.TestCase):
    def test_normalizes(self):
        self.assertEqual(ch.validate_domain(" Example.COM. "), "example.com")

    def test_subdomain_ok(self):
        self.assertEqual(ch.validate_domain("api.example.co.uk"), "api.example.co.uk")

    def test_rejects_empty_and_single_label(self):
        for bad in ("", ".", "localhost", "com"):
            with self.assertRaises(ValueError):
                ch.validate_domain(bad)

    def test_rejects_wildcard(self):
        with self.assertRaises(ValueError):
            ch.validate_domain("*.example.com")

    def test_rejects_shell_metacharacters(self):
        # These would be injection if they ever reached a shell; they never
        # get past validation (and nothing here uses a shell anyway).
        for bad in ("example.com;id", "$(whoami).com", "example.com`id`",
                    "exa mple.com", "example.com/CN=evil", "-example.com"):
            with self.assertRaises(ValueError):
                ch.validate_domain(bad)

    def test_rejects_underscore_label(self):
        # Underscores belong in _acme-challenge names, not issuable hostnames.
        with self.assertRaises(ValueError):
            ch.validate_domain("_acme-challenge.example.com")


class SanSet(unittest.TestCase):
    def test_dns01_is_apex_plus_www(self):
        self.assertEqual(ch.san_set("example.com", "dns-01"), ["example.com", "www.example.com"])

    def test_http01_is_apex_only(self):
        self.assertEqual(ch.san_set("example.com", "http-01"), ["example.com"])


class OpensslReqArgs(unittest.TestCase):
    def test_argv_shape(self):
        args = ch.openssl_req_args("example.com", ["example.com", "www.example.com"], "/k", "/c")
        self.assertEqual(args[:2], ["openssl", "req"])
        self.assertIn("-subj", args)
        self.assertEqual(args[args.index("-subj") + 1], "/CN=example.com")
        self.assertEqual(args[args.index("-addext") + 1],
                         "subjectAltName=DNS:example.com,DNS:www.example.com")
        self.assertEqual(args[args.index("-keyout") + 1], "/k")
        self.assertEqual(args[args.index("-out") + 1], "/c")
        # An argv list, not a string - nothing for a shell to expand.
        self.assertIsInstance(args, list)


class CountPemCerts(unittest.TestCase):
    def test_counts(self):
        block = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----\n"
        self.assertEqual(ch.count_pem_certs(block * 3), 3)
        self.assertEqual(ch.count_pem_certs("not a pem"), 0)


CERT_TEXT = """\
Certificate:
    Data:
        Validity
            Not Before: Apr  6 12:00:00 2026 GMT
            Not After : Jul  5 12:00:00 2026 GMT
        X509v3 extensions:
            X509v3 Subject Alternative Name:
                DNS:example.com, DNS:www.example.com
"""


class ParseCertText(unittest.TestCase):
    def test_extracts_sans_and_not_after(self):
        parsed = ch.parse_cert_text(CERT_TEXT)
        self.assertEqual(parsed["sans"], ["example.com", "www.example.com"])
        self.assertEqual(parsed["not_after"], "Jul  5 12:00:00 2026 GMT")

    def test_missing_sections_do_not_crash(self):
        parsed = ch.parse_cert_text("garbage")
        self.assertEqual(parsed["sans"], [])
        self.assertIsNone(parsed["not_after"])

    def test_non_dns_entries_ignored(self):
        text = CERT_TEXT.replace("DNS:example.com, DNS:www.example.com",
                                 "IP Address:1.2.3.4, DNS:example.com")
        self.assertEqual(ch.parse_cert_text(text)["sans"], ["example.com"])


class CoversDomain(unittest.TestCase):
    def test_exact_and_case(self):
        self.assertTrue(ch.covers_domain(["example.com"], "Example.COM"))

    def test_absent(self):
        self.assertFalse(ch.covers_domain(["other.com"], "example.com"))
        self.assertFalse(ch.covers_domain([], "example.com"))

    def test_wildcard_covers_one_level(self):
        self.assertTrue(ch.covers_domain(["*.example.com"], "www.example.com"))
        self.assertFalse(ch.covers_domain(["*.example.com"], "example.com"))
        self.assertFalse(ch.covers_domain(["*.example.com"], "a.b.example.com"))

    def test_suffix_confusion_rejected(self):
        self.assertFalse(ch.covers_domain(["notexample.com"], "example.com"))


class DaysRemaining(unittest.TestCase):
    NOW = dt.datetime(2026, 7, 1, 12, 0, 0, tzinfo=dt.timezone.utc)

    def test_counts_days(self):
        self.assertEqual(ch.days_remaining("Jul  5 12:00:00 2026 GMT", now=self.NOW), 4)

    def test_unparseable_returns_none(self):
        self.assertIsNone(ch.days_remaining("someday", now=self.NOW))


@unittest.skipUnless(HAVE_OPENSSL, "openssl not installed")
class CsrEndToEnd(unittest.TestCase):
    def _run(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = ch.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_generates_key_0600_and_matching_csr(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, _ = self._run(["csr", "--domain", "example.com",
                                    "--challenge", "dns-01", "--dir", tmp])
            self.assertEqual(rc, 0, out)
            key = os.path.join(tmp, "example.com.key")
            csr = os.path.join(tmp, "example.com.csr")
            self.assertTrue(os.path.exists(key))
            self.assertEqual(stat.S_IMODE(os.stat(key).st_mode), 0o600)
            req = subprocess.run(["openssl", "req", "-in", csr, "-noout", "-text"],
                                 capture_output=True, text=True)
            self.assertEqual(req.returncode, 0)
            self.assertIn("DNS:example.com", req.stdout)
            self.assertIn("DNS:www.example.com", req.stdout)

    def test_existing_key_is_backed_up_not_clobbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = os.path.join(tmp, "example.com.key")
            with open(key, "w") as f:
                f.write("OLD KEY MATERIAL")
            rc, _, _ = self._run(["csr", "--domain", "example.com",
                                  "--challenge", "http-01", "--dir", tmp])
            self.assertEqual(rc, 0)
            baks = [p for p in os.listdir(tmp) if p.endswith(".bak")]
            self.assertEqual(len(baks), 1)
            with open(os.path.join(tmp, baks[0])) as f:
                self.assertEqual(f.read(), "OLD KEY MATERIAL")
            with open(key) as f:
                self.assertIn("PRIVATE KEY", f.read())

    def test_bad_domain_rejected_before_openssl(self):
        rc, _, err = self._run(["csr", "--domain", "$(whoami).com",
                                "--challenge", "dns-01", "--dir", "/nonexistent-never-created"])
        self.assertEqual(rc, 2)
        self.assertIn("refusing", err)
        self.assertFalse(os.path.exists("/nonexistent-never-created"))


@unittest.skipUnless(HAVE_OPENSSL, "openssl not installed")
class VerifyChainEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.chain = os.path.join(cls.tmp, "chain.pem")
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3",
             "-keyout", os.path.join(cls.tmp, "k.pem"), "-out", cls.chain,
             "-subj", "/CN=example.com",
             "-addext", "subjectAltName=DNS:example.com,DNS:www.example.com"],
            check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            rc = ch.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_matching_chain_accepted(self):
        rc, out, _ = self._run(["verify-chain", "--domain", "example.com",
                                "--challenge", "dns-01", "--chain-file", self.chain])
        self.assertEqual(rc, 0, out)
        self.assertIn('"covers_domain": true', out)
        self.assertIn("www.example.com", out)

    def test_wrong_domain_rejected(self):
        # The core check: a chain for some other domain must not be blessed.
        rc, _, err = self._run(["verify-chain", "--domain", "other.com",
                                "--challenge", "dns-01", "--chain-file", self.chain])
        self.assertEqual(rc, 2)
        self.assertIn("does NOT cover", err)

    def test_garbage_file_rejected(self):
        garbage = os.path.join(self.tmp, "garbage.pem")
        with open(garbage, "w") as f:
            f.write("this is not a certificate")
        rc, _, err = self._run(["verify-chain", "--domain", "example.com",
                                "--challenge", "dns-01", "--chain-file", garbage])
        self.assertEqual(rc, 2)
        self.assertIn("no PEM certificate", err)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for the changelog extractor used by the release workflow."""
import unittest

from extract_changelog import extract

SAMPLE = """\
# Changelog

Intro line that must never leak into a release body.

## [0.4.0] - current

Headline for 0.4.0.

### Added
- Thing one.
- Thing two.

## [0.3.0] - 2026-01-02

Older release.

## [0.2.0]

Even older, no date suffix.
"""


class ExtractChangelogTest(unittest.TestCase):
    def test_extracts_section_without_heading(self):
        out = extract(SAMPLE, "0.4.0")
        self.assertIn("Headline for 0.4.0.", out)
        self.assertIn("- Thing one.", out)
        # Stops before the next version and never includes the file intro.
        self.assertNotIn("Older release.", out)
        self.assertNotIn("Intro line", out)
        self.assertFalse(out.startswith("##"))

    def test_matches_with_date_suffix(self):
        out = extract(SAMPLE, "0.3.0")
        self.assertEqual(out, "Older release.")

    def test_matches_bare_heading_no_suffix(self):
        out = extract(SAMPLE, "0.2.0")
        self.assertEqual(out, "Even older, no date suffix.")

    def test_missing_version_returns_none(self):
        self.assertIsNone(extract(SAMPLE, "9.9.9"))

    def test_partial_version_does_not_false_match(self):
        # "0.4" must not match the "0.4.0" heading.
        self.assertIsNone(extract(SAMPLE, "0.4"))


if __name__ == "__main__":
    unittest.main()

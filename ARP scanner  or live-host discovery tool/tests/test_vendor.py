"""Tests for vendor lookup."""
import tempfile
import unittest
from pathlib import Path

from arpscan.vendor import load_vendor_db, lookup_vendor


class TestLookupVendor(unittest.TestCase):
    def test_known_oui(self):
        self.assertEqual(lookup_vendor("b8:27:eb:aa:bb:cc"), "Raspberry Pi Foundation")

    def test_case_and_separator_insensitive(self):
        self.assertEqual(lookup_vendor("B8-27-EB-AA-BB-CC"), "Raspberry Pi Foundation")

    def test_unknown_returns_none(self):
        self.assertIsNone(lookup_vendor("00:00:5e:00:53:01"))

    def test_custom_db_overrides(self):
        self.assertEqual(lookup_vendor("b8:27:eb:aa:bb:cc", db={"B827EB": "Custom"}), "Custom")


class TestLoadVendorDb(unittest.TestCase):
    def test_loads_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oui.txt"
            path.write_text(
                "# comment\n"
                "001122 Vendor One\n"
                "ab:cd:ef Vendor Two\n"
                "\n",
                encoding="utf-8",
            )
            db = load_vendor_db(str(path))
            self.assertEqual(db, {"001122": "Vendor One", "ABCDEF": "Vendor Two"})


if __name__ == "__main__":
    unittest.main()
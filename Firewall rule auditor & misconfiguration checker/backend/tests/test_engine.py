"""Golden-check unit tests for the FRAMC engine (see memory.md §5)."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.engine import audit

SAMPLES = os.path.join(ROOT, "samples")


def sample(name: str) -> str:
    with open(os.path.join(SAMPLES, name), encoding="utf-8") as fh:
        return fh.read()


def audit_file(name: str, fmt: str):
    return audit(fmt, sample(name), name=name)


class IptablesSmoke(unittest.TestCase):
    def test_parse_count(self):
        r = audit_file("iptables.txt", "iptables")
        self.assertGreaterEqual(len(r["rules"]), 12)

    def test_critical_present(self):
        r = audit_file("iptables.txt", "iptables")
        sevs = {f["severity"] for f in r["findings"]}
        self.assertIn("CRITICAL", sevs)

    def test_posture_low(self):
        r = audit_file("iptables.txt", "iptables")
        self.assertLess(r["posture"]["score"], 60)


class AsaSmoke(unittest.TestCase):
    def test_parse_and_shadow(self):
        r = audit_file("cisco_asa.txt", "cisco-asa")
        self.assertEqual(len(r["rules"]), 5)
        cats = {f["category"] for f in r["findings"]}
        self.assertIn("shadowed", cats)


class FortigateSmoke(unittest.TestCase):
    def test_resolves_objects_and_override(self):
        r = audit_file("fortigate.txt", "fortigate")
        self.assertEqual(len(r["rules"]), 5)
        self.assertTrue(any(x["src_ip"] == "10.0.0.0/8" for x in r["rules"]))
        cats = {f["category"] for f in r["findings"]}
        self.assertIn("override", cats)


class WindowsSmoke(unittest.TestCase):
    def test_duplicate_and_no_log(self):
        r = audit_file("windows.txt", "windows")
        self.assertEqual(len(r["rules"]), 5)  # disabled rule skipped
        cats = [f["category"] for f in r["findings"]]
        self.assertIn("duplicate", cats)


class PfsenseSmoke(unittest.TestCase):
    def test_world_open(self):
        r = audit_file("pfsense.txt", "pfsense")
        self.assertEqual(len(r["rules"]), 4)
        self.assertTrue(any(f["category"] == "permissive"
                            for f in r["findings"]))


class PaloAltoSmoke(unittest.TestCase):
    def test_parses(self):
        r = audit_file("paloalto.txt", "paloalto")
        self.assertEqual(len(r["rules"]), 5)


class PlainSmoke(unittest.TestCase):
    def test_shadow(self):
        r = audit_file("plain.txt", "plain")
        self.assertEqual(len(r["rules"]), 7)
        self.assertTrue(any(f["category"] == "shadowed"
                            for f in r["findings"]))


class Determinism(unittest.TestCase):
    def test_same_input_same_report(self):
        a = audit_file("iptables.txt", "iptables")
        b = audit_file("iptables.txt", "iptables")
        self.assertEqual(a["findings"], b["findings"])
        self.assertEqual(a["rules"], b["rules"])


class EmptyInput(unittest.TestCase):
    def test_empty_content(self):
        r = audit("iptables", "")
        self.assertEqual(r["rules"], [])
        self.assertGreaterEqual(len(r["findings"]), 0)


if __name__ == "__main__":
    unittest.main()
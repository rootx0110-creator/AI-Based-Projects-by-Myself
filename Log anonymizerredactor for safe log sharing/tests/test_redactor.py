"""Headless unit checks for the redaction engine.

Usage:
    python tests/test_redactor.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.html_report import build_html_report  # noqa: E402
from core.redactor import Redactor  # noqa: E402


def mask(text: str, enabled=None, strategy="mask") -> str:
    return Redactor(strategy=strategy).redact(text, enabled=enabled).text


def only(modes, text, strategy="mask"):
    m = dict.fromkeys(Redactor.MODES, False)
    for k in modes:
        m[k] = True
    return Redactor(strategy=strategy).redact(text, enabled=m)


class TestMasking(unittest.TestCase):
    def test_ipv4(self):
        out = only(["ipv4"], "from 192.168.1.42 ok")
        self.assertEqual(out.text, "from 192*** ok")
        self.assertEqual(out.counts["ipv4"], 1)

    def test_ipv6_compressed(self):
        out = only(["ipv6"], "on 2001:db8::ff00:42:8329")
        self.assertIn("200***", out.text)
        self.assertNotIn("ff00", out.text)

    def test_ipv6_no_false_port(self):
        out = only(["ipv6"], "udp://10.0.0.7:9000")
        self.assertNotIn("9000***", out.text)
        self.assertIn(":9000", out.text)

    def test_email(self):
        out = only(["email"], "mail jane.doe@acme-corp.com now")
        self.assertEqual(out.text, "mail jan*** now")

    def test_phone_preserves_date(self):
        out = only(["phone"], "[2026-09-15 08:41:02] call +1 (555) 013-4488")
        self.assertNotIn("2026-09-15***", out.text)
        self.assertNotIn("08:41:02***", out.text)
        self.assertIn("+1 ***", out.text)

    def test_pan_full_card(self):
        out = only(["pan"], "card 4111 1111 1111 1111 exp")
        self.assertEqual(out.text, "card 411*** exp")

    def test_ssn(self):
        out = only(["ssn"], "found 047-59-9911")
        self.assertEqual(out.text, "found 047***")

    def test_uuid(self):
        out = only(["uuid"], "id 9f8c4a7f-2e1b-4c3d-9a5e-b1f2a3c4d5e6")
        self.assertEqual(out.text, "id 9f8***")

    def test_jwt(self):
        tok = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        out = only(["jwt"], f"bearer {tok}")
        self.assertNotIn("SflKxwRJSMeK", out.text)
        self.assertEqual(out.counts["jwt"], 1)

    def test_passwd_keeps_prefix(self):
        out = only(["passwd"], "password=Hunt3r2!Password using")
        self.assertEqual(out.text, "password=Hun*** using")

    def test_arn_not_phone(self):
        out = Redactor().redact("arn:aws:iam::123456789012:role/deployer")
        self.assertNotIn("123456789012", out.text)
        if "123456789012" not in out.text:
            pass

    def test_no_double_mask_latlon(self):
        out = Redactor().redact("Geo lat=37.7749 lon=-122.4194")
        self.assertNotIn("******", out.text)
        self.assertIn("lon=-12***", out.text)

    def test_all_strategies(self):
        text = "ip 10.0.0.1 mail a@b.co"
        for s in ("mask", "full", "hash", "token"):
            out = Redactor(strategy=s).redact(text)
            self.assertGreater(out.total_redactions, 0, s)
            self.assertNotIn("10.0.0.1", out.text, s)
            self.assertNotIn("a@b.co", out.text, s)

    def test_deterministic(self):
        t = "ip 10.0.0.1 secret=hunter2"
        self.assertEqual(Redactor().redact(t).text, Redactor().redact(t).text)

    def test_no_raise_on_garbage(self):
        for junk in ("", "\n", "a" * 3000, "中文日志 测试 🎉", "\x00\x01\x02"):
            Redactor().redact(junk)

    def test_html_report_never_leaks(self):
        text = "login jane.doe@corp.com from 192.168.1.1 pass=hunterH1!"
        r = Redactor().redact(text)
        doc = build_html_report(r, {"strategy": "mask", "enabled": {}},
                                text)
        for secret in ("jane.doe@corp.com", "192.168.1.1", "hunterH1!"):
            self.assertNotIn(secret, doc)
        self.assertIn("<html", doc.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
"""Tests for output formatters."""
import csv
import io
import json
import unittest

from arpscan.models import Host
from arpscan.output import format_csv, format_json, format_hosts, format_table


class TestFormatTable(unittest.TestCase):
    def test_header_and_rows(self):
        out = format_table(
            [
                Host(ip="192.168.1.1", mac="a4:2b:b0:93:1c:2d", vendor="Dell"),
                Host(ip="192.168.1.2", mac="b8:27:eb:aa:bb:cc"),
            ]
        )
        self.assertIn("IP", out)
        self.assertIn("MAC address", out)
        self.assertIn("192.168.1.1", out)
        self.assertIn("a4:2b:b0:93:1c:2d", out)
        self.assertIn("Dell", out)

    def test_empty(self):
        self.assertEqual(format_table([]), "No live hosts found.\n")


class TestFormatJson(unittest.TestCase):
    def test_roundtrip(self):
        hosts = [Host(ip="192.168.1.1", mac="a4:2b:b0:93:1c:2d", vendor="Dell")]
        data = json.loads(format_json(hosts))
        self.assertEqual(data, [{"ip": "192.168.1.1", "mac": "a4:2b:b0:93:1c:2d", "vendor": "Dell"}])


class TestFormatCsv(unittest.TestCase):
    def test_roundtrip(self):
        hosts = [Host(ip="192.168.1.1", mac="a4:2b:b0:93:1c:2d", vendor="Dell")]
        reader = csv.DictReader(io.StringIO(format_csv(hosts)))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ip"], "192.168.1.1")
        self.assertEqual(rows[0]["vendor"], "Dell")


class TestFormatHosts(unittest.TestCase):
    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            format_hosts([], fmt="xml")


if __name__ == "__main__":
    unittest.main()
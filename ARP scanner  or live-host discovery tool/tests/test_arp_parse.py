"""Tests for ARP table text parsers."""
import unittest

from arpscan.arp_parse import normalize_mac, parse_arp_output

WINDOWS_SAMPLE = """\
Interface: 192.168.1.5 --- 0x5
  Internet Address      Physical Address      Type
  192.168.1.1           a4-2b-b0-93-1c-2d     dynamic
  192.168.1.2           b8-27-eb-aa-bb-cc     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
  224.0.0.251           01-00-5e-00-00-fb     static
"""

LINUX_IP_SAMPLE = """\
192.168.1.1 dev eth0 lladdr a4:2b:b0:93:1c:2d REACHABLE
192.168.1.2 dev eth0 lladdr b8:27:eb:aa:bb:cc STALE
192.168.1.3 dev eth0 FAILED
192.168.1.255 dev eth0 lladdr ff:ff:ff:ff:ff:ff PERMANENT
"""

POSIX_ARP_SAMPLE = """\
? (192.168.1.1) at a4:2b:b0:93:1c:2d on en0 ifscope [ethernet]
? (192.168.1.2) at b8:27:eb:aa:bb:cc on en0 ifscope [ethernet]
? (192.168.1.255) at ff:ff:ff:ff:ff:ff on en0 ifscope [ethernet]
"""


class TestNormalizeMac(unittest.TestCase):
    def test_dash_to_colon(self):
        self.assertEqual(normalize_mac("A4-2B-B0-93-1C-2D"), "a4:2b:b0:93:1c:2d")

    def test_colon_lowercase(self):
        self.assertEqual(normalize_mac("A4:2B:B0:93:1C:2D"), "a4:2b:b0:93:1c:2d")


class TestParseWindows(unittest.TestCase):
    def test_parses_hosts_and_filters_bogus(self):
        result = parse_arp_output(WINDOWS_SAMPLE, family="windows")
        self.assertEqual(
            result,
            {
                "192.168.1.1": "a4:2b:b0:93:1c:2d",
                "192.168.1.2": "b8:27:eb:aa:bb:cc",
            },
        )


class TestParseLinuxIp(unittest.TestCase):
    def test_parses_reachable_and_stale(self):
        result = parse_arp_output(LINUX_IP_SAMPLE, family="linux-ip")
        self.assertEqual(
            result,
            {
                "192.168.1.1": "a4:2b:b0:93:1c:2d",
                "192.168.1.2": "b8:27:eb:aa:bb:cc",
            },
        )

    def test_failed_entry_without_mac_skipped(self):
        result = parse_arp_output("192.168.1.9 dev eth0 FAILED", family="linux-ip")
        self.assertEqual(result, {})


class TestParsePosixArp(unittest.TestCase):
    def test_parses_hosts(self):
        result = parse_arp_output(POSIX_ARP_SAMPLE, family="posix-arp")
        self.assertEqual(
            result,
            {
                "192.168.1.1": "a4:2b:b0:93:1c:2d",
                "192.168.1.2": "b8:27:eb:aa:bb:cc",
            },
        )


class TestUnknownFamily(unittest.TestCase):
    def test_raises(self):
        with self.assertRaises(ValueError):
            parse_arp_output("x", family="nope")


if __name__ == "__main__":
    unittest.main()
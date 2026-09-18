"""Tests for target expansion."""
import ipaddress
import unittest

from arpscan.network import expand_target, expand_targets


class TestExpandTarget(unittest.TestCase):
    def test_single_ip(self):
        self.assertEqual(expand_target("192.168.1.1"), [ipaddress.IPv4Address("192.168.1.1")])

    def test_cidr(self):
        addrs = expand_target("192.168.1.0/30")
        self.assertEqual([str(a) for a in addrs], ["192.168.1.1", "192.168.1.2"])

    def test_cidr_host_bits_ok(self):
        addrs = expand_target("192.168.1.7/30")
        self.assertEqual([str(a) for a in addrs], ["192.168.1.5", "192.168.1.6"])

    def test_range_full(self):
        addrs = expand_target("192.168.1.10-192.168.1.12")
        self.assertEqual([str(a) for a in addrs], ["192.168.1.10", "192.168.1.11", "192.168.1.12"])

    def test_range_last_octet_shorthand(self):
        addrs = expand_target("192.168.1.10-12")
        self.assertEqual([str(a) for a in addrs], ["192.168.1.10", "192.168.1.11", "192.168.1.12"])

    def test_range_backwards_raises(self):
        with self.assertRaises(ValueError):
            expand_target("192.168.1.50-192.168.1.10")

    def test_range_too_large_raises(self):
        with self.assertRaises(ValueError):
            expand_target("10.0.0.1-10.1.255.254")

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            expand_target("not-an-ip")

    def test_empty(self):
        self.assertEqual(expand_target("   "), [])


class TestExpandTargets(unittest.TestCase):
    def test_mixed_and_dedup(self):
        addrs = expand_targets(["192.168.1.0/30", "192.168.1.2"])
        self.assertEqual([str(a) for a in addrs], ["192.168.1.1", "192.168.1.2"])

    def test_comma_separated(self):
        addrs = expand_targets(["192.168.1.1,192.168.1.2"])
        self.assertEqual([str(a) for a in addrs], ["192.168.1.1", "192.168.1.2"])


if __name__ == "__main__":
    unittest.main()
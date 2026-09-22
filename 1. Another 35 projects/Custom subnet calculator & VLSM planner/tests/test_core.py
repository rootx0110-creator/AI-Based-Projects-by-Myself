"""Unit tests for app/core.py — headless, no GUI required."""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import core
from app.core import (PlanOverflowError, VlsmSegment, calculate_subnet,
                      derive_subnets, int_to_ip, ip_to_int, mask_to_prefix,
                      prefix_from_hosts, prefix_from_subnets, prefix_to_mask,
                      prefix_to_wildcard, validate_ip, validate_prefix,
                      vlsm_plan)


class TestIPUtils(unittest.TestCase):
    def test_roundtrip(self):
        for ip in ("0.0.0.0", "10.10.10.10", "192.168.1.254", "255.255.255.255"):
            self.assertEqual(int_to_ip(ip_to_int(ip)), ip)

    def test_validate(self):
        self.assertTrue(validate_ip("8.8.8.8"))
        self.assertFalse(validate_ip("999.1.1.1"))
        self.assertFalse(validate_ip("1.2.3"))
        self.assertFalse(validate_ip("a.b.c.d"))
        self.assertTrue(validate_prefix(0))
        self.assertTrue(validate_prefix(32))
        self.assertFalse(validate_prefix(33))
        self.assertFalse(validate_prefix("24"))

    def test_mask_prefix(self):
        self.assertEqual(mask_to_prefix("255.255.255.0"), 24)
        self.assertEqual(mask_to_prefix("255.255.255.255"), 32)
        self.assertEqual(mask_to_prefix("0.0.0.0"), 0)
        with self.assertRaises(ValueError):
            mask_to_prefix("255.0.255.0")

    def test_prefix_to_mask_wildcard(self):
        self.assertEqual(prefix_to_mask(24), "255.255.255.0")
        self.assertEqual(prefix_to_mask(0), "0.0.0.0")
        self.assertEqual(prefix_to_mask(32), "255.255.255.255")
        self.assertEqual(prefix_to_wildcard(24), "0.0.0.255")
        self.assertEqual(prefix_to_wildcard(0), "255.255.255.255")
        with self.assertRaises(ValueError):
            prefix_to_mask(40)


class TestCalculateSubnet(unittest.TestCase):
    def test_classic(self):
        s = calculate_subnet("192.168.1.5", 26)
        self.assertEqual(s["network"], "192.168.1.0")
        self.assertEqual(s["broadcast"], "192.168.1.63")
        self.assertEqual(s["first_usable"], "192.168.1.1")
        self.assertEqual(s["last_usable"], "192.168.1.62")
        self.assertEqual(s["mask"], "255.255.255.192")
        self.assertEqual(s["wildcard"], "0.0.0.63")
        self.assertEqual(s["usable_hosts"], 62)
        self.assertEqual(s["total_addresses"], 64)
        self.assertEqual(s["class"], "C")
        self.assertEqual(s["borrowed_bits"], 2)
        self.assertEqual(s["subnets_in_class"], 4)

    def test_class_b(self):
        s = calculate_subnet("172.16.5.200", 16)
        self.assertEqual(s["network"], "172.16.0.0")
        self.assertEqual(s["broadcast"], "172.16.255.255")
        self.assertEqual(s["class"], "B")
        self.assertEqual(s["mask"], "255.255.0.0")

    def test_class_b_borrowed(self):
        s = calculate_subnet("172.16.5.200", 20)
        self.assertEqual(s["network"], "172.16.0.0")
        self.assertEqual(s["broadcast"], "172.16.15.255")
        self.assertEqual(s["borrowed_bits"], 4)
        self.assertEqual(s["subnets_in_class"], 16)

    def test_class_a(self):
        s = calculate_subnet("10.1.2.3", 8)
        self.assertEqual(s["network"], "10.0.0.0")
        self.assertEqual(s["broadcast"], "10.255.255.255")
        self.assertEqual(s["usable_hosts"], 16777214)

    def test_rfc3021(self):
        s31 = calculate_subnet("192.168.1.5", 31)
        self.assertEqual(s31["usable_hosts"], 2)
        self.assertEqual(s31["first_usable"], "192.168.1.4")
        self.assertEqual(s31["last_usable"], "192.168.1.5")
        s32 = calculate_subnet("10.0.0.7", 32)
        self.assertEqual(s32["usable_hosts"], 1)
        self.assertEqual(s32["broadcast"], "10.0.0.7")
        self.assertEqual(s32["network"], "10.0.0.7")

    def test_slash0(self):
        s = calculate_subnet("192.168.1.1", 0)
        self.assertEqual(s["network"], "0.0.0.0")
        self.assertEqual(s["broadcast"], "255.255.255.255")
        self.assertEqual(s["total_addresses"], 4294967296)

    def test_binary_bits(self):
        s = calculate_subnet("192.168.1.1", 24)
        self.assertEqual(s["network_bits"], 24)
        self.assertEqual(s["host_bits"], 8)
        self.assertEqual(s["mask_binary"], "1" * 24 + "0" * 8)


class TestReverseModes(unittest.TestCase):
    def test_prefix_from_hosts(self):
        self.assertEqual(prefix_from_hosts(2), 30)
        self.assertEqual(prefix_from_hosts(6), 29)
        self.assertEqual(prefix_from_hosts(14), 28)
        self.assertEqual(prefix_from_hosts(62), 26)
        self.assertEqual(prefix_from_hosts(254), 24)

    def test_prefix_from_subnets(self):
        self.assertEqual(prefix_from_subnets(1), 0)
        self.assertEqual(prefix_from_subnets(2), 1)
        self.assertEqual(prefix_from_subnets(4), 2)
        self.assertEqual(prefix_from_subnets(8), 3)


class TestDeriveSubnets(unittest.TestCase):
    def test_count(self):
        r = derive_subnets("192.168.1.5", 26)
        self.assertEqual(r["total"], 4)
        self.assertEqual(len(r["subnets"]), 4)
        self.assertFalse(r["truncated"])
        self.assertEqual(r["subnets"][0]["network"], "192.168.1.0")
        self.assertEqual(r["subnets"][0]["broadcast"], "192.168.1.63")
        self.assertEqual(r["subnets"][-1]["network"], "192.168.1.192")

    def test_truncation(self):
        r = derive_subnets("10.0.0.0", 16, max_rows=50)
        self.assertTrue(r["truncated"])
        self.assertEqual(r["total"], 256)
        self.assertEqual(len(r["subnets"]), 50)

    def test_slash32(self):
        r = derive_subnets("10.0.0.7", 32)
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["subnets"][0]["network"], "10.0.0.7")


class TestVLSM(unittest.TestCase):
    def _plan(self, base="192.168.10.0", pfx=24, segs=(
            ("A", 25), ("B", 12), ("C", 30), ("D", 2))):
        return vlsm_plan(base, pfx, [VlsmSegment(n, h) for n, h in segs])

    def test_textbook(self):
        plan = self._plan()
        self.assertEqual(plan.base_network, "192.168.10.0")
        self.assertFalse(plan.overflow)
        self.assertEqual(len(plan.allocations), 4)
        first = {a.name: a for a in plan.allocations}
        self.assertEqual(first["C"].prefix, 27)
        self.assertEqual(first["A"].prefix, 27)
        self.assertEqual(first["B"].prefix, 28)
        self.assertEqual(first["D"].prefix, 30)
        self.assertEqual(first["C"].network, "192.168.10.0")
        self.assertEqual(first["C"].usable, 30)

    def test_block_sizes(self):
        plan = self._plan()
        sizes = {a.name: a.block_size for a in plan.allocations}
        self.assertEqual(sizes["A"], 32)
        self.assertEqual(sizes["B"], 16)
        self.assertEqual(sizes["D"], 4)

    def test_overflow_raises(self):
        with self.assertRaises(PlanOverflowError) as ctx:
            vlsm_plan("10.0.0.0", 24, [VlsmSegment("huge", 500)])
        self.assertEqual(ctx.exception.deficit, 512)

    def test_overflow_partial(self):
        plan = vlsm_plan("10.0.0.0", 24,
                         [VlsmSegment("fit", 50), VlsmSegment("huge", 500)],
                         raise_on_overflow=False)
        self.assertTrue(plan.overflow)
        self.assertEqual(plan.deficit, 512)
        self.assertEqual(len(plan.allocations), 1)
        self.assertEqual(plan.allocations[0].name, "fit")

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            vlsm_plan("192.168.1.1", 30, [VlsmSegment("a", 2)])
        with self.assertRaises(ValueError):
            vlsm_plan("192.168.1.0", 24, [VlsmSegment("a", 0)])

    def test_largest_first_allocation_order(self):
        segs = [("Small", 5), ("Huge", 120), ("Mid", 60)]
        plan = vlsm_plan("172.16.0.0", 24, [VlsmSegment(n, h) for n, h in segs])
        nets = [a.network for a in plan.allocations]
        self.assertEqual(nets, ["172.16.0.0", "172.16.0.128", "172.16.0.192"])
        order = {a.name: a.block_size for a in plan.allocations}
        self.assertEqual(order["Huge"], 128)


if __name__ == "__main__":
    unittest.main(verbosity=2)
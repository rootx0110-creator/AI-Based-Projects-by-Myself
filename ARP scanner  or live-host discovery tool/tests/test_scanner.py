"""Tests for the scanner orchestrator and backend selection."""
import unittest
from unittest import mock

from arpscan.backends import BackendError
from arpscan.models import Host
from arpscan.scanner import Scanner, select_backend


class FakeBackend:
    """Backend double: returns canned (ip, mac) pairs for targets."""

    name = "fake"

    def __init__(self, results):
        # results: list of (ip, mac) tuples; duplicates allowed to test dedupe.
        self.results = results
        self.called_with = None

    def scan(self, targets, timeout=2.0, retries=1):
        self.called_with = (list(targets), timeout, retries)
        target_set = set(targets)
        return [
            Host(ip=ip, mac=mac) for ip, mac in self.results if ip in target_set
        ]


class TestScanner(unittest.TestCase):
    def test_expands_targets_and_passes_to_backend(self):
        backend = FakeBackend([("192.168.1.2", "a4:2b:b0:93:1c:2d")])
        scanner = Scanner(backend, do_vendor=False)
        hosts = scanner.scan(["192.168.1.0/30"], timeout=3.0, retries=2)
        self.assertEqual([h.ip for h in hosts], ["192.168.1.2"])
        self.assertEqual(backend.called_with[0], ["192.168.1.1", "192.168.1.2"])
        self.assertEqual(backend.called_with[1], 3.0)
        self.assertEqual(backend.called_with[2], 2)

    def test_dedupes_and_sorts_by_ip(self):
        backend = FakeBackend(
            [
                ("192.168.1.10", "aa:aa:aa:aa:aa:aa"),
                ("192.168.1.2", "bb:bb:bb:bb:bb:bb"),
                ("192.168.1.10", "cc:cc:cc:cc:cc:cc"),  # duplicate IP, first wins
            ]
        )
        scanner = Scanner(backend, do_vendor=False)
        hosts = scanner.scan(["192.168.1.0/24"])
        self.assertEqual([h.ip for h in hosts], ["192.168.1.2", "192.168.1.10"])
        self.assertEqual(hosts[1].mac, "aa:aa:aa:aa:aa:aa")

    def test_vendor_enrichment(self):
        backend = FakeBackend([("192.168.1.2", "b8:27:eb:aa:bb:cc")])
        scanner = Scanner(backend, do_vendor=True)
        hosts = scanner.scan(["192.168.1.2"])
        self.assertEqual(hosts[0].vendor, "Raspberry Pi Foundation")

    def test_no_targets_returns_empty_without_calling_backend(self):
        backend = FakeBackend({})
        scanner = Scanner(backend, do_vendor=False)
        self.assertEqual(scanner.scan([]), [])
        self.assertIsNone(backend.called_with)


class TestSelectBackend(unittest.TestCase):
    def test_explicit_system(self):
        self.assertEqual(select_backend("system").name, "system")

    def test_explicit_scapy(self):
        self.assertEqual(select_backend("scapy").name, "scapy")

    def test_auto_falls_back_when_scapy_missing(self):
        with mock.patch("arpscan.scanner.ScapyBackend", side_effect=BackendError("no scapy")):
            self.assertEqual(select_backend("auto").name, "system")

    def test_auto_prefers_scapy(self):
        self.assertEqual(select_backend("auto").name, "scapy")


if __name__ == "__main__":
    unittest.main()
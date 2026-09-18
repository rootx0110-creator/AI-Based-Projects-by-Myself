"""Tests for the CLI."""
import unittest
from unittest import mock

from arpscan.backends import BackendError
from arpscan.cli import main
from arpscan.models import Host


class TestCli(unittest.TestCase):
    def test_requires_target_or_auto(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_prints_results(self):
        fake_backend = mock.Mock()
        fake_backend.name = "fake"
        fake_backend.scan.return_value = [
            Host(ip="192.168.1.2", mac="a4:2b:b0:93:1c:2d", vendor="Dell")
        ]
        with mock.patch("arpscan.cli.select_backend", return_value=fake_backend):
            with mock.patch("sys.stdout") as stdout:
                rc = main(["192.168.1.2"])
        self.assertEqual(rc, 0)
        stdout.write.assert_called_once()
        self.assertIn("192.168.1.2", stdout.write.call_args[0][0])

    def test_json_format(self):
        fake_backend = mock.Mock()
        fake_backend.name = "fake"
        fake_backend.scan.return_value = [
            Host(ip="192.168.1.2", mac="a4:2b:b0:93:1c:2d")
        ]
        with mock.patch("arpscan.cli.select_backend", return_value=fake_backend):
            with mock.patch("sys.stdout") as stdout:
                rc = main(["192.168.1.2", "--format", "json", "--no-vendor"])
        self.assertEqual(rc, 0)
        self.assertIn('"ip": "192.168.1.2"', stdout.write.call_args[0][0])

    def test_auto_detects_local_network(self):
        fake_backend = mock.Mock()
        fake_backend.name = "fake"
        fake_backend.scan.return_value = []
        with mock.patch("arpscan.cli.select_backend", return_value=fake_backend):
            with mock.patch(
                "arpscan.cli.detect_local_networks",
                return_value=["192.168.1.0/24"],
            ) as detect:
                with mock.patch("sys.stdout"):
                    rc = main(["--auto", "--no-vendor"])
        self.assertEqual(rc, 0)
        detect.assert_called_once()
        # The /24 is expanded before reaching the backend.
        targets = fake_backend.scan.call_args[0][0]
        self.assertEqual(len(targets), 254)
        self.assertEqual(targets[0], "192.168.1.1")
        self.assertEqual(targets[-1], "192.168.1.254")

    def test_auto_falls_back_on_backend_error(self):
        failing = mock.Mock()
        failing.name = "scapy"
        failing.scan.side_effect = BackendError("no raw-packet privileges")
        good = mock.Mock()
        good.name = "system"
        good.scan.return_value = []
        with mock.patch(
            "arpscan.cli.select_backend", side_effect=[failing, good]
        ):
            with mock.patch("sys.stdout"):
                rc = main(["192.168.1.2"])
        self.assertEqual(rc, 0)
        self.assertEqual(failing.scan.call_count, 1)
        good.scan.assert_called_once()


if __name__ == "__main__":
    unittest.main()
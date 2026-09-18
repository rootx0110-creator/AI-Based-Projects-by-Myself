"""Tests for local network auto-detection parsers."""
import unittest

from arpscan.localnet import (
    detect_local_networks,
    parse_ifconfig,
    parse_ip_addr,
    parse_ipconfig,
)

IPCONFIG_SAMPLE = """
Windows IP Configuration


Ethernet adapter Ethernet0:

   Connection-specific DNS Suffix  . :
   Link-local IPv6 Address . . . . . : fe80::1234
   IPv4 Address. . . . . . . . . . . : 192.168.1.5
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1

Ethernet adapter Loopback Pseudo-Interface 1:

   IPv4 Address. . . . . . . . . . . : 127.0.0.1
   Subnet Mask . . . . . . . . . . . : 255.0.0.0
"""

IP_ADDR_SAMPLE = """\
2: eth0    inet 192.168.1.5/24 brd 192.168.1.255 scope global dynamic eth0
3: docker0 inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
1: lo      inet 127.0.0.1/8 scope host lo
"""

IFCONFIG_SAMPLE = """\
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	inet 192.168.1.5 netmask 0xffffff00 broadcast 192.168.1.255
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
	inet 127.0.0.1 netmask 0xff000000
"""


class TestParseIpconfig(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(parse_ipconfig(IPCONFIG_SAMPLE), [("192.168.1.5", 24), ("127.0.0.1", 8)])


class TestParseIpAddr(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(
            parse_ip_addr(IP_ADDR_SAMPLE),
            [("192.168.1.5", 24), ("172.17.0.1", 16), ("127.0.0.1", 8)],
        )


class TestParseIfconfig(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(parse_ifconfig(IFCONFIG_SAMPLE), [("192.168.1.5", 24), ("127.0.0.1", 8)])


class TestDetectLocalNetworks(unittest.TestCase):
    def test_returns_non_loopback(self):
        import unittest.mock as mock

        import arpscan.localnet as localnet

        with mock.patch.object(localnet.sys, "platform", "linux"), mock.patch.object(
            localnet, "_run", lambda cmd: IP_ADDR_SAMPLE
        ):
            networks = detect_local_networks()
        nets = [str(n) for n in networks]
        self.assertIn("192.168.1.0/24", nets)
        self.assertIn("172.17.0.0/16", nets)
        self.assertNotIn("127.0.0.0/8", nets)


if __name__ == "__main__":
    unittest.main()
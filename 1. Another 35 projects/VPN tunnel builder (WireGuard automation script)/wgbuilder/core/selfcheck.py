"""Script-based engine verification: `python -m wgbuilder.core.selfcheck`."""

import sys
import tempfile
import os

from wgbuilder.core import keys, x25519, configs, report


def check(cond: bool, label: str) -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {label}")
    if not cond:
        sys.exit(1)


def run() -> None:
    print("=== VPN Tunnel Builder selfcheck ===")

    # Crypto is self-verified at import; still verify a known wg-style pair.
    p1, q1 = keys.generate_keypair()
    check(keys.is_valid_key(p1) and keys.is_valid_key(q1), "generated keys are base64-valid")
    check(keys.derive_public(p1) == q1, "derive_public matches generated public key")

    # Determinism: same private -> same public
    check(keys.derive_public(p1) == keys.derive_public(p1), "derivation is deterministic")

    # RFC 7748 vector is asserted inside x25519 import; here check clamping parity:
    raw = bytes(range(32))
    pub_a = x25519.scalarbase(raw)
    cloned = bytearray(raw)[:]; cloned[0] &= 248; cloned[31] &= 127; cloned[31] |= 64
    pub_b = x25519.scalarbase(bytes(cloned))
    check(pub_a == pub_b, "scalarbase clamps identically twice (idempotent)")

    # Config round-trip
    server = {
        "private_key": p1, "public_key": q1, "listen_port": 51820, "address": "10.0.0.1",
        "mtu": 1420, "dns": "1.1.1.1", "endpoint_host": "vpn.example.com",
        "post_up": "", "post_down": "",
    }
    p2, q2 = keys.generate_keypair()
    p3, q3 = keys.generate_keypair()
    peers = [
        {"name": "b", "ip": "10.0.0.2", "allowed_ips": "10.0.0.2/32", "public_key": q2, "keepalive": 25},
        {"name": "a", "ip": "10.0.0.3", "allowed_ips": "10.0.0.3/32", "public_key": q3, "keepalive": 25},
    ]
    sconf = configs.build_server_config(server, peers)
    parsed = configs.parse_config(sconf)
    check(parsed["Interface"]["ListenPort"] == "51820", "server config round-trips port")
    check(len(parsed["Peers"]) == 2 and parsed["Peers"][0]["PublicKey"] == q3,
          "server config lists peers sorted by name")

    peer = {"name": "phone", "ip": "10.0.0.2", "private_key": p2, "public_key": q2,
            "keepalive": 25, "allowed_ips": "10.0.0.2/32"}
    cconf = configs.build_client_config(server, peer, "VPN Tunnel Builder")
    cparsed = configs.parse_config(cconf)
    check(cparsed["Interface"]["PrivateKey"] == p2, "client config carries peer key")
    check(cparsed["Peers"][0]["Endpoint"] == "vpn.example.com:51820", "client endpoint built")

    # Auto-assign math
    taken = ["10.0.0.1"]
    nxt = list(configs.next_peer_candidates("10.0.0.0/24", taken))[:3]
    check(nxt == ["10.0.0.2", "10.0.0.3", "10.0.0.4"], "peer auto-assignment")
    check(configs.describe_subnet("10.0.0.0/24").startswith("10.0.0.0/24"),
          "subnet description renders")

    # Report generation (incl. QR images embedded as data URIs)
    state = {
        "server": dict(server), "peers": list(peers), "exports": [],
        "settings": {},
    }
    state["server"]["private_key"] = p1
    state["server"]["public_key"] = q1
    for pk, qk, pcfg in zip((p2, p3), (q2, q3), state["peers"]):
        pcfg["private_key"] = pk
    html_doc = report.build_report(
        state, [{"at": "2026-09-18T10:00:00+00:00", "level": "info", "message": "selfcheck"}])
    check("VPN Tunnel Builder" in html_doc and "data:image/png;base64," in html_doc
          and "10.0.0.2/32" in html_doc,
          "HTML report self-contained with embedded QR + configs")

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, report.default_filename())
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html_doc)
        check(os.path.getsize(path) > 2000, "report downloads to file")

    print("=== selfcheck OK ===")


if __name__ == "__main__":
    run()
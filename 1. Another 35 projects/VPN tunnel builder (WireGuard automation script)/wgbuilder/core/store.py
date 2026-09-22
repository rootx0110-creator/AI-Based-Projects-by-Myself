"""JSON persistence for server settings, peers, settings, exports, event log."""

import copy
import datetime as _dt
import json
import os
import tempfile
import uuid

import wgbuilder.core.keys as keys

APP_NAME = "VPNTunnelBuilder"
MAX_EVENTS = 200


def default_data_folder() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Store:
    """Owned by the app; mutated via the App controller then written back."""

    def __init__(self, data_folder: str | None = None):
        self.data_folder = data_folder or default_data_folder()
        self.path = os.path.join(self.data_folder, "state.json")
        self.server = {
            "interface_name": "wg0",
            "listen_port": 51820,
            "subnet": "10.0.0.0/24",
            "address": "10.0.0.1",
            "endpoint_host": "",
            "dns": "1.1.1.1",
            "mtu": 1420,
            "private_key": "",
            "public_key": "",
            "post_up": "",
            "post_down": "",
            "created_at": "",
            "updated_at": "",
        }
        self.settings = {
            "default_dns": "1.1.1.1",
            "default_mtu": 1420,
            "default_keepalive": 25,
            "data_folder": self.data_folder,
            "wg_cli_path": "",
        }
        self.peers: list[dict] = []
        self.exports: list[dict] = []
        self.events: list[dict] = []
        self._loaded_from = None

    # ---- lifecycle -----------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            self._new_state()
            self._bootstrap_server_keys()
            self.log("info", "Fresh state created - generated server keypair")
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            self.log("warn", "State file unreadable; starting fresh")
            self._new_state()
            self._bootstrap_server_keys()
            self.save()
            return
        self._apply(data)
        self._ensure_invariants()
        self.log("info", "State loaded")

    def _new_state(self):
        self.server = {
            "interface_name": "wg0",
            "listen_port": 51820,
            "subnet": "10.0.0.0/24",
            "address": "10.0.0.1",
            "endpoint_host": "",
            "dns": self.settings.get("default_dns", "1.1.1.1"),
            "mtu": self.settings.get("default_mtu", 1420),
            "private_key": "",
            "public_key": "",
            "post_up": "",
            "post_down": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.peers = []
        self.exports = []
        self.events = []

    def _apply(self, data: dict):
        srv = data.get("server") or {}
        for k in self.server:
            if k in srv:
                self.server[k] = srv[k]
        if data.get("settings"):
            self.settings.update(data["settings"])
        self.peers = [dict(p) for p in (data.get("peers") or [])]
        self.exports = [dict(e) for e in (data.get("exports") or [])]
        self.events = [dict(e) for e in (data.get("events") or [])][-MAX_EVENTS:]

    def save(self):
        os.makedirs(self.data_folder, exist_ok=True)
        payload = {
            "server": self.server,
            "settings": self.settings,
            "peers": self.peers,
            "exports": self.exports,
            "events": self.events[-MAX_EVENTS:],
        }
        fd, tmp = tempfile.mkstemp(dir=self.data_folder, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ---- invariants ----------------------------------------------------
    def _ensure_invariants(self):
        need_save = False
        if not self.server.get("private_key") or not self.server.get("public_key"):
            self._bootstrap_server_keys()
            need_save = True
        expected_pub = derive_pub_or_none(self.server.get("private_key", ""))
        if expected_pub and expected_pub != self.server.get("public_key"):
            self.server["public_key"] = expected_pub
            need_save = True
        for p in self.peers:
            exp = derive_pub_or_none(p.get("private_key", ""))
            if exp and p.get("public_key") != exp:
                p["public_key"] = exp
                need_save = True
        if need_save:
            self.save()

    def _bootstrap_server_keys(self):
        priv, pub = keys.generate_keypair()
        self.server["private_key"] = priv
        self.server["public_key"] = pub
        self.server["created_at"] = self.server["created_at"] or _now()
        self.server["updated_at"] = _now()

    # ---- domain helpers -------------------------------------------------
    def log(self, level: str, message: str):
        self.events.append({"at": _now(), "level": level, "message": message})

    def set_server_keypair(self, priv_b64: str):
        self.server["private_key"] = priv_b64.strip()
        self.server["public_key"] = keys.derive_public(priv_b64.strip())
        self.server["updated_at"] = _now()
        self.log("info", "Server keypair set")

    def new_peer(self, name: str, ip: str | None = None, keepalive: int = 25) -> dict:
        priv, pub = keys.generate_keypair()
        peer = {
            "id": uuid.uuid4().hex,
            "name": name.strip(),
            "ip": ip,
            "allowed_ips": "",
            "keepalive": int(keepalive),
            "private_key": priv,
            "public_key": pub,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.peers.append(peer)
        self.log("info", f"Peer added: {peer['name']}")
        return peer

    def remove_peer(self, peer_id: str):
        before = len(self.peers)
        self.peers = [p for p in self.peers if p["id"] != peer_id]
        if len(self.peers) != before:
            self.log("info", "Peer removed")

    def rotate_peer_keys(self, peer_id: str):
        for p in self.peers:
            if p["id"] == peer_id:
                priv, pub = keys.generate_keypair()
                p["private_key"] = priv
                p["public_key"] = pub
                p["updated_at"] = _now()
                self.log("info", f"Keys rotated for {p['name']}")
                return p
        return None

    def peer(self, peer_id: str):
        for p in self.peers:
            if p["id"] == peer_id:
                return p
        return None

    def record_export(self, folder: str, peer_count: int):
        self.exports.append({
            "at": _now(), "folder": folder, "peer_count": peer_count,
        })
        self.log("info", f"Exported {peer_count} peer config(s) -> {folder}")

    def snapshot(self) -> dict:
        return copy.deepcopy({
            "server": self.server, "peers": self.peers,
            "exports": self.exports, "settings": self.settings,
        })


def derive_pub_or_none(priv_b64: str) -> str:
    try:
        return keys.derive_public(priv_b64)
    except (ValueError, TypeError):
        return ""
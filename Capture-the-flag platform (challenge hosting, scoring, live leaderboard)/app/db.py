"""JSON file-backed database with in-process locking.

Designed for offline / single-server deployments (perfect for an EXE build).
All writes are atomic (write to temp, then os.replace) so a crash never
corrupts the store.
"""
import json
import os
import secrets
import threading
from datetime import datetime, timezone

from . import config


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = __import__("hashlib").pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


class JSONDatabase:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = self._load_or_seed()

    # ------------------------------------------------------------- persistence
    def _load_or_seed(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass  # fall through and reseed
        data = self._seed()
        self._atomic_write(data)
        return data

    def _atomic_write(self, data: dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self.path)

    def save(self) -> None:
        with self._lock:
            self._atomic_write(self._data)

    # ------------------------------------------------------------------- seed
    def _seed(self) -> dict:
        now = utcnow_iso()
        challenges = [
            dict(id=1, title="Welcome to the Grid", category="warmup", points=100,
                 description="Every CTF starts somewhere. The flag is hiding in plain sight right on this page.",
                 flag="flag{welcome_to_the_grid}", dynamic=False, hidden=False,
                 flag_hint=None, created_at=now),
            dict(id=2, title="Base Camp", category="encoding", points=150,
                 description="A strange message arrived encoded: ZmxhZ3tiYXNlNjRfaXNfZWFzeX0= Decode it.",
                 flag="flag{base64_is_easy}", dynamic=False, hidden=False,
                 flag_hint="Base64 decode", created_at=now),
            dict(id=3, title="Caesar's Salad", category="crypto", points=200,
                 description="A strange inscription was found: synt{pnrfne_jnf_urer}. Romans spoke 13 letters at a time.",
                 flag="flag{caesar_was_here}", dynamic=False, hidden=False,
                 flag_hint="ROT13", created_at=now),
            dict(id=4, title="Robots Have Secrets", category="web", points=250,
                 description="A webmaster left a note for crawlers at /robots.txt on the demo site. What is disallowed?",
                 flag="flag{robots_txt_ftw}", dynamic=False, hidden=False,
                 flag_hint="Check robots.txt", created_at=now),
            dict(id=5, title="Power Surge", category="pwn", points=500,
                 description="Dynamic scoring challenge. The more teams solve it, the fewer points it pays. Flag: flag{dynamic_decay}",
                 flag="flag{dynamic_decay}", dynamic=True, hidden=False,
                 flag_hint=None, created_at=now),
            dict(id=6, title="Ghost in the Feed", category="forensics", points=350,
                 description="Someone hid a flag inside the live activity feed events. Find the anomaly.",
                 flag="flag{feed_watcher}", dynamic=False, hidden=False,
                 flag_hint="Watch the websocket feed", created_at=now),
        ]
        return {
            "config": {"ctf_name": "NEON GRID CTF", "started_at": now,
                       "registration_open": True, "competition_open": True},
            "users": [],   # id, username, password_hash, is_admin, created_at
            "submissions": [],  # id, user_id, challenge_id, submitted, correct, ip, submitted_at
            "challenges": challenges,
            "next_ids": {"user": 1, "submission": 1},
        }

    # ------------------------------------------------------------------ users
    def create_user(self, username: str, password: str, is_admin: bool = False):
        with self._lock:
            uid = self._data["next_ids"]["user"]
            self._data["next_ids"]["user"] += 1
            user = dict(id=uid, username=username, password_hash=hash_password(password),
                        is_admin=is_admin, created_at=utcnow_iso())
            self._data["users"].append(user)
            self.save()
            return user

    def get_user_by_name(self, username: str):
        username = (username or "").strip().lower()
        for u in self._data["users"]:
            if u["username"].lower() == username:
                return u
        return None

    def get_user(self, uid: int):
        for u in self._data["users"]:
            if u["id"] == uid:
                return u
        return None

    def all_users(self):
        return list(self._data["users"])

    # ------------------------------------------------------- challenge helpers
    def all_challenges(self):
        return list(self._data["challenges"])

    def get_challenge(self, cid: int):
        for c in self._data["challenges"]:
            if c["id"] == cid:
                return c
        return None

    def create_challenge(self, **fields) -> dict:
        with self._lock:
            ids = [c["id"] for c in self._data["challenges"]]
            cid = (max(ids) + 1) if ids else 1
            ch = dict(id=cid, title=fields["title"], category=fields.get("category", "misc"),
                      points=int(fields.get("points", 100)),
                      description=fields.get("description", ""),
                      flag=fields["flag"], dynamic=bool(fields.get("dynamic", False)),
                      hidden=bool(fields.get("hidden", False)),
                      flag_hint=fields.get("flag_hint"), created_at=utcnow_iso())
            self._data["challenges"].append(ch)
            self.save()
            return ch

    def update_challenge(self, cid: int, **fields) -> bool:
        with self._lock:
            ch = self.get_challenge(cid)
            if not ch:
                return False
            for key in ("title", "category", "points", "description", "flag",
                        "dynamic", "hidden", "flag_hint"):
                if key in fields and fields[key] is not None:
                    ch[key] = fields[key]
            self.save()
            return True

    def delete_challenge(self, cid: int) -> bool:
        with self._lock:
            before = len(self._data["challenges"])
            self._data["challenges"] = [c for c in self._data["challenges"] if c["id"] != cid]
            changed = len(self._data["challenges"]) != before
            if changed:
                self.save()
            return changed

    # ------------------------------------------------------------ submissions
    def add_submission(self, user_id: int, challenge_id: int, submitted: str,
                       correct: bool, ip: str = "") -> dict:
        with self._lock:
            sid = self._data["next_ids"]["submission"]
            self._data["next_ids"]["submission"] += 1
            sub = dict(id=sid, user_id=user_id, challenge_id=challenge_id,
                       submitted=submitted, correct=correct, ip=ip,
                       submitted_at=utcnow_iso())
            self._data["submissions"].append(sub)
            self.save()
            return sub

    def all_submissions(self):
        return list(self._data["submissions"])

    def user_solved_ids(self, user_id: int) -> set:
        return {s["challenge_id"] for s in self._data["submissions"]
                if s["user_id"] == user_id and s["correct"]}

    def solves_for_challenge(self, challenge_id: int):
        return [s for s in self._data["submissions"]
                if s["challenge_id"] == challenge_id and s["correct"]]

    def user_solve_count(self, user_id: int) -> int:
        return len(self.user_solved_ids(user_id))

    # ------------------------------------------------------------- scoreboard
    def scoreboard(self):
        """Returns list of dicts: id, name, score, solves, last_solve_at, rank.
        Sorted by score desc, then earliest last solve (CTF-style tiebreak)."""
        users = {u["id"]: u for u in self._data["users"] if not u["is_admin"]}
        rows = []
        for uid, u in users.items():
            solves = [s for s in self._data["submissions"]
                      if s["user_id"] == uid and s["correct"]]
            score = 0
            last_at = None
            for s in solves:
                ch = self.get_challenge(s["challenge_id"])
                if not ch:
                    continue
                if ch.get("dynamic"):
                    n = len(self.solves_for_challenge(ch["id"]))
                    pts = max(config.DYNAMIC_MINIMUM,
                              ch["points"] - config.DYNAMIC_SLOPE * (n - 1))
                else:
                    pts = ch["points"]
                score += pts
                if last_at is None or s["submitted_at"] > last_at:
                    last_at = s["submitted_at"]
            rows.append(dict(id=uid, name=u["username"], score=score,
                             solves=len(solves), last_solve_at=last_at))
        rows.sort(key=lambda r: (-r["score"], r["last_solve_at"] or "9999"))
        for i, r in enumerate(rows, start=1):
            r["rank"] = i
        return rows

    # ------------------------------------------------------------------- misc
    def ctf_config(self) -> dict:
        return dict(self._data["config"])

    def set_ctf_config(self, **fields) -> None:
        with self._lock:
            self._data["config"].update(fields)
            self.save()

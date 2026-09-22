import os
import sqlite3
import json
from contextlib import closing
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS challenges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    category    TEXT NOT NULL,
    difficulty  TEXT NOT NULL DEFAULT 'Easy',
    description TEXT NOT NULL DEFAULT '',
    flag        TEXT NOT NULL DEFAULT '',
    hints       TEXT NOT NULL DEFAULT '[]',
    status      TEXT NOT NULL DEFAULT 'todo',
    source      TEXT NOT NULL DEFAULT 'seed',
    created_at  TEXT NOT NULL,
    solved_at   TEXT
);
CREATE TABLE IF NOT EXISTS hint_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL,
    level        INTEGER NOT NULL,
    source       TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seed_challenges():
    return [
        {
            "title": "Login Bypass 101",
            "category": "Web",
            "difficulty": "Easy",
            "flag": "ctf{sql_1nj3ct10n}",
            "description": (
                "A training site has a login form that queries the back end like this:\n\n"
                "    SELECT * FROM users WHERE user='<input>' AND pass='<input>'\n\n"
                "Your goal is to log in as 'admin' without knowing the password."
            ),
            "hints": [
                "Think about how the quotes in the SQL query are handled. What happens if the "
                "username itself contains a single quote?",
                "Try ending the username early with a quote, then add a condition that is always "
                "true, for example `admin' OR 1=1 --`. The `--` comments out the rest of the query.",
                "A working payload is often `admin' OR '1'='1` or `admin' OR 1=1 -- `. Copy the "
                "pattern, not the answer: you only need the WHERE clause to be true.",
            ],
        },
        {
            "title": "Hidden Vault",
            "category": "Web",
            "difficulty": "Medium",
            "flag": "ctf{c00k13_m0n5t3r}",
            "description": (
                "The admin console at /vault is 'not in the sitemap'. The server returns 403 until "
                "you look like an admin. Inspect everything the client sends."
            ),
            "hints": [
                "Robots are polite and ask first. Have you asked /robots.txt to introduce the site?",
                "Robots told you a path, but the server still says no. What little key/value pairs "
                "does the browser attach to every request, and where do they live?",
                "The server checks the 'role' cookie, not the session. If you can set cookies, you "
                "can become a special privileged user. The flag format should guide the format.",
            ],
        },
        {
            "title": "Caesar's Secret",
            "category": "Crypto",
            "difficulty": "Easy",
            "flag": "ctf{caesar_is_easy}",
            "description": (
                "You intercepted the ciphertext:\n\n"
                "    wjm{tgfztk_an_tsrf}\n\n"
                "It looks like rotations are involved."
            ),
            "hints": [
                "A Caesar shift maps each letter to another letter some fixed distance away in the "
                "alphabet. Try shifting the first four letters 'wjm{' mentally... 'w' one step back "
                "is 'v'.",
                "There are only 25 possible shifts. Shift the text by 8 backward to see a familiar "
                "prefix.",
                "Shifting every letter 8 positions back restores it. Note punctuation like { } stays "
                "in place.",
            ],
        },
        {
            "title": "XOR Bytes",
            "category": "Crypto",
            "difficulty": "Medium",
            "flag": "ctf{xor_xor_double_cross}",
            "description": (
                "A message was encrypted with a single repeated byte:\n\n"
                "    1b 0d 62 14 05 09 4c 70 06 02 4a 02 10 0b 4e 34 0e 0d 4a 03 4f 0e 4d\n\n"
                "Repeating-key XOR with a one-byte key leaves the distribution of the original "
                "plaintext intact."
            ),
            "hints": [
                "One-byte XOR means every plaintext byte is XORed with the same key byte. The "
                "plaintext is probably ASCII text that starts with 'ctf{'.",
                "XOR the first byte 0x1b with 'c' (0x63) to recover the key. (0x1b ^ 0x63 = 0x78 = 'x'.)",
                "With key 0x78, XOR every byte. ASCII printable text should pop out immediately.",
            ],
        },
        {
            "title": "Pieced Together",
            "category": "Forensics",
            "difficulty": "Easy",
            "flag": "ctf{not_a_png}",
            "description": (
                "An image file `artifact.bin` on the desktop won't open despite ending in .bin. "
                "Trainers renamed it on purpose. Look at the first bytes of the file."
            ),
            "hints": [
                "Every file format starts with a signature (magic bytes). What are the first hex "
                "bytes of a PNG?",
                "A PNG starts with 89 50 4E 47 (JPEG starts with FF D8 FF). When the extension does "
                "not match the signature, many tools still respect the signature.",
                "Recognizing the type is enough; you do not actually need to open it. The answer "
                "should start with ctf{ and rhyme with what the file really is.",
            ],
        },
        {
            "title": "Hidden Stream",
            "category": "Forensics",
            "difficulty": "Medium",
            "flag": "ctf{lsb_whispers}",
            "description": (
                "A BMP photo contains a hidden message. Trainers used the least-significant-bit "
                "trick: each pixel's low bit carries one bit of the hidden text."
            ),
            "hints": [
                "Look at the least significant bit (LSB) of each color channel, across pixels "
                "in order.",
                "Collect one bit per byte/channel into groups of 8 to form ASCII characters. "
                "Benign-looking images hide text this way because the change is invisible.",
                "Reading the low bit of, say, the red channel for every pixel and packing 8 bits "
                "at a time reveals human-readable text."
            ],
        },
        {
            "title": "Gatekeeper",
            "category": "Reversing",
            "difficulty": "Hard",
            "flag": "ctf{g4t3k33p3r}",
            "description": (
                "You have a small binary. When you know the check, spot that the comparison is "
                "over a transformed copy of your input. Trainers shipped the source to the trainer "
                "console."
            ),
            "hints": [
                "In the trainer console you can view the source: the program XORs each input byte "
                "with 0x2A and compares to a constant string.",
                "Find the constant string in the binary data/console (e.g. Jg}n`oa8...). That is "
                "the XOR-mangled flag.",
                "XOR the constant with 0x2A byte-by-byte to recover the flag. Same trick as XOR "
                "Bytes, applied to a compiled program.",
            ],
        },
        {
            "title": "Digits & Lies",
            "category": "OSINT",
            "difficulty": "Easy",
            "flag": "ctf{ak_bl4ck_p0ppy}",
            "description": (
                "A poster in the lab shows a handler handle: `@blackpoppy`. The account bio links "
                "a digital archive. Search the name and the archive index for the flag."
            ),
            "hints": [
                "Search engines index public pages. Try the exact handle plus the platform name.",
                "The bio mentions an 'archive'. Archives often use predictable URLs. Try the main "
                "index first, then search engine caches.",
                "The flag is composed of initials: the first letters of the words in the bio line "
                "'Amber Kite - Black Poppy'. Follow that pattern and wrap in ctf{}.",
            ],
        },
        {
            "title": "Welcome Beacon",
            "category": "Misc",
            "difficulty": "Easy",
            "flag": "ctf{w3lc0m3_b34c0n}",
            "description": (
                "The welcome page beacon image has an encoded string under it:\n\n"
                "    NXR8d3dsYzBtM19iMzRjMG59\n\n"
                "It looks like a standard ASCII encoding with a '=' at the end."
            ),
            "hints": [
                "Base64 output only uses A-Z, a-z, 0-9, +, / and padding '='.",
                "Decode it with any base64 decoder to get the flag in ctf{...} form.",
                "Yes, it is that easy. NXR8... decodes to ctf{w3lc0m3_b34c0n}.",
            ],
        },
    ]


class Store:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self):
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            n = conn.execute("SELECT COUNT(*) AS c FROM challenges").fetchone()["c"]
            if n == 0:
                for i, ch in enumerate(seed_challenges(), 1):
                    conn.execute(
                        "INSERT INTO challenges (title, category, difficulty, description, flag, "
                        "hints, status, source, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (ch["title"], ch["category"], ch["difficulty"], ch["description"],
                         ch["flag"], json.dumps(ch["hints"]), "todo", "seed", _now()),
                    )
                for key, val in {
                    "provider": "local",
                    "base_url": "",
                    "api_key": "",
                    "model": "",
                    "enabled": "0",
                }.items():
                    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (key, val))
                conn.commit()

    def challenges(self, status=None, category=None, q=None):
        sql = "SELECT * FROM challenges"
        where, args = [], []
        if status:
            where.append("status = ?")
            args.append(status)
        if category:
            where.append("category = ?")
            args.append(category)
        if q:
            where.append("(title LIKE ? OR description LIKE ?)")
            like = f"%{q}%"
            args += [like, like]
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id"
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, args).fetchall()
        return [self._row_dict(r, conn if False else None) for r in rows]

    def _row_dict(self, row, _conn):
        d = dict(row)
        d["hints_json"] = json.loads(d.get("hints") or "[]")
        return d

    def get_challenge(self, cid):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM challenges WHERE id = ?", (cid,)).fetchone()
            if not row:
                return None
            return self._row_dict(row, conn)

    def hint_count(self, cid):
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT COUNT(*) AS c FROM hint_log WHERE challenge_id = ?", (cid,)
            ).fetchone()["c"]

    def hint_history(self, cid):
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM hint_log WHERE challenge_id = ? ORDER BY id", (cid,)
            ).fetchall()
        return [dict(r) for r in rows]

    def recent_hints(self, limit=8):
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT h.*, c.title AS challenge_title, c.category AS challenge_category "
                "FROM hint_log h JOIN challenges c ON c.id = h.challenge_id "
                "ORDER BY h.id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def log_hint(self, cid, level, source, content):
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO hint_log (challenge_id, level, source, content, created_at) "
                "VALUES (?,?,?,?,?)",
                (cid, level, source, content, _now()),
            )
            conn.execute("UPDATE challenges SET status = ? WHERE id = ? AND status = ?",
                         ("in_progress", cid, "todo"))
            conn.commit()

    def verify_solve(self, cid, answer):
        ch = self.get_challenge(cid)
        if not ch:
            return None
        correct = answer.strip().lower() == ch["flag"].strip().lower()
        with closing(self._connect()) as conn:
            if correct:
                conn.execute(
                    "UPDATE challenges SET status='solved', solved_at=? WHERE id=?",
                    (_now(), cid))
            conn.commit()
        return {"correct": correct, "status": "solved" if correct else ch["status"]}

    def add_challenge(self, title, category, difficulty, description, flag, hints):
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO challenges (title, category, difficulty, description, flag, hints, "
                "status, source, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (title, category, difficulty, description, flag, json.dumps(hints),
                 "todo", "user", _now()))
            conn.commit()
            return cur.lastrowid

    def mark_solved(self, cid):
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE challenges SET status='solved', solved_at=? WHERE id=?",
                (_now(), cid))
            conn.commit()

    def set_setting(self, key, value):
        with closing(self._connect()) as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
            conn.commit()

    def get_settings(self):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        s = {"provider": "local", "base_url": "", "api_key": "", "model": "", "enabled": "0"}
        for r in rows:
            s[r["key"]] = r["value"]
        return s

    def stats(self):
        with closing(self._connect()) as conn:
            total = conn.execute("SELECT COUNT(*) c FROM challenges").fetchone()["c"]
            solved = conn.execute("SELECT COUNT(*) c FROM challenges WHERE status='solved'").fetchone()["c"]
            inprog = conn.execute("SELECT COUNT(*) c FROM challenges WHERE status='in_progress'").fetchone()["c"]
            hints = conn.execute("SELECT COUNT(*) c FROM hint_log").fetchone()["c"]
            ai_hints = conn.execute("SELECT COUNT(*) c FROM hint_log WHERE source='ai'").fetchone()["c"]
            local = conn.execute("SELECT COUNT(*) c FROM hint_log WHERE source IN ('local','authored')").fetchone()["c"]
            cats = conn.execute("SELECT category, COUNT(*) c FROM challenges GROUP BY category ORDER BY c DESC").fetchall()
            recent_solved = conn.execute(
                "SELECT title, category, solved_at FROM challenges WHERE status='solved' AND solved_at IS NOT NULL "
                "ORDER BY solved_at DESC LIMIT 5").fetchall()
        return {
            "total": total, "solved": solved, "in_progress": inprog,
            "todo": total - solved - inprog, "hints": hints, "ai_hints": ai_hints,
            "local_hints": local,
            "categories": [dict(r) for r in cats],
            "recent_solved": [dict(r) for r in recent_solved],
        }

    def report_data(self):
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT c.id, c.title, c.category, c.difficulty, c.status, c.source, c.created_at, "
                "c.solved_at, "
                "(SELECT COUNT(*) FROM hint_log h WHERE h.challenge_id = c.id) AS hint_count, "
                "(SELECT COUNT(*) FROM hint_log h WHERE h.challenge_id = c.id AND h.source='ai') AS ai_count "
                "FROM challenges c ORDER BY c.id").fetchall()
            log = conn.execute(
                "SELECT h.id, h.challenge_id, c.title AS challenge_title, h.level, h.source, "
                "h.content, h.created_at FROM hint_log h JOIN challenges c ON c.id=h.challenge_id "
                "ORDER BY h.id").fetchall()
        return [dict(r) for r in rows], [dict(r) for r in log]
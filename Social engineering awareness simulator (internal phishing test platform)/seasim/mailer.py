"""Local SMTP stub for SeaSim.

Runs a tiny SMTP server on 127.0.0.1:8025 that accepts messages and
prints them to the in-app log. It is a *stub*: it never relays anywhere
and binds only to the loopback interface. The engine's delivery thread
hands each simulated email to :class:`SmtpMailer`, which performs a
best-effort conversation with the stub (and silently ignores failures
so the simulation continues even if the stub is not running).
"""

from __future__ import annotations

import re
import socket
import threading
from datetime import datetime
from typing import Callable, List, Optional

from seasim import constants as C
from seasim.safety import ensure_local_only

_CRLF_RE = re.compile(r"\r?\n")


class SmtpMailer:
    """Sends simulated emails to the local stub (best-effort)."""

    def __init__(self, host: str = C.SMTP_HOST, port: int = C.SMTP_PORT,
                 sender: str = C.SMTP_SENDER,
                 from_name: str = C.SMTP_FROM_NAME) -> None:
        ensure_local_only(host, port)
        self.host = host
        self.port = port
        self.sender = sender
        self.from_name = from_name

    def build_message(self, to_addr: str, subject: str, body: str) -> str:
        body = body.replace("\n", "\r\n")
        return (
            f"From: {self.from_name} <{self.sender}>\r\n"
            f"To: <{to_addr}>\r\n"
            f'Subject: {subject}\r\n'
            f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S')} \r\n"
            f"X-Mailer: SeaSim-Simulator (no external relay)\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n"
            f"\r\n"
            f"{body}\r\n"
        )

    def send(self, to_addr: str, subject: str, body: str) -> bool:
        """Best-effort delivery to the loopback stub. Never raises."""
        msg = self.build_message(to_addr, subject, body)
        try:
            with socket.create_connection((self.host, self.port), timeout=1.5) as s:
                s.sendall(msg.encode("utf-8"))
            return True
        except OSError:
            return False

    def send_many(self, items: List[tuple]) -> int:
        ok = 0
        for to_addr, subject, body in items:
            if self.send(to_addr, subject, body):
                ok += 1
        return ok


class LocalSmtpStub:
    """Loopback-only sink server. Accepts messages, logs them, discards."""

    def __init__(self, host: str = C.SMTP_HOST, port: int = C.SMTP_PORT,
                 logger: Optional[Callable[[str], None]] = None) -> None:
        ensure_local_only(host, port)
        self.host = host
        self.port = port
        self._logger = logger or (lambda line: None)
        self._srv: Optional[socket.socket] = None
        self.bound_port: int = port
        self._threads: List[threading.Thread] = []
        self.count = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()

    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Bind to the first free port in [port, port+10] (loopback only)."""
        self._stop.clear()
        for attempt in range(11):
            port = self.port + attempt
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind((self.host, port))
                srv.listen(8)
                srv.settimeout(0.5)
                self._srv = srv
                self.bound_port = port
                break
            except OSError:
                try:
                    srv.close()
                except OSError:
                    pass
                continue
        else:
            self._srv = None
            self.bound_port = -1
        if self._srv is None:
            self._logger(f"[smtp-stub] could not bind {self.host}:"
                         f"{self.port}-{self.port + 10}")
            return False
        t = threading.Thread(target=self._accept_loop, name="smtp-stub",
                             daemon=True)
        t.start()
        self._threads.append(t)
        self._logger(f"[smtp-stub] listening on {self.host}:"
                     f"{self.bound_port} (loopback only, nothing is "
                     f"relayed)")
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._srv is not None:
            try:
                self._srv.close()
            except OSError:
                pass
            self._srv = None

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            if self._srv is None:
                break
            try:
                conn, addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            if addr[0] not in ("127.0.0.1", "::1"):
                try:
                    conn.close()
                except OSError:
                    pass
                self._logger(f"[smtp-stub] refused non-local {addr[0]}")
                continue
            t = threading.Thread(target=self._handle, args=(conn,),
                                 daemon=True)
            t.start()
            self._threads.append(t)

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(5)
            buf = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > 2_000_000:
                    break
            text = buf.decode("utf-8", errors="replace")
            with self._lock:
                self.count += 1
                n = self.count
            subject = ""
            to = ""
            for line in _CRLF_RE.split(text):
                low = line.lower()
                if low.startswith("subject:"):
                    subject = line[8:].strip()
                elif low.startswith("to:"):
                    to = line[3:].strip()
            first = _CRLF_RE.split(text.strip())[-1][:100] if text.strip() else ""
            self._logger(f"[smtp-stub] #{n} -> {to or '?'} | "
                         f"subject: {subject or '(none)'} | {first}...")
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

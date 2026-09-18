"""Application configuration with JSON persistence."""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import (
    BIND_MODES,
    BUFFER_SIZE,
    BUFFER_SIZES,
    CONNECT_TIMEOUT,
    DEFAULT_HTTP_PORT,
    DEFAULT_SOCKS_PORT,
    ErrorCode,
)


def app_dir() -> Path:
    """Directory that hosts the .exe (frozen) or the project root (source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_dir() / "config.json"


@dataclass
class ProxyConfig:
    http_port: int = DEFAULT_HTTP_PORT
    socks_port: int = DEFAULT_SOCKS_PORT
    buffer_size: int = BUFFER_SIZE
    connect_timeout: float = CONNECT_TIMEOUT
    bind_mode: str = "localhost"          # "localhost" | "lan"

    auth_enabled: bool = False            # require user/pass from clients
    username: str = ""
    password: str = ""

    upstream_enabled: bool = False        # chain through another proxy
    upstream_kind: str = "http"           # "http" (CONNECT) | "socks5"
    upstream_host: str = ""
    upstream_port: int = 1080
    upstream_username: str = ""
    upstream_password: str = ""

    theme_mode: str = "dark"              # "dark" | "light"
    autoscroll: bool = True

    # ------------------------------------------------------------- helpers
    @property
    def bind_host(self) -> str:
        return "0.0.0.0" if self.bind_mode == "lan" else "127.0.0.1"

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, port in (("HTTP port", self.http_port), ("SOCKS5 port", self.socks_port)):
            if not isinstance(port, int) or not 1 <= port <= 65535:
                errors.append(f"{name} must be an integer between 1 and 65535")
        if self.http_port == self.socks_port:
            errors.append("HTTP and SOCKS5 ports must be different")
        if self.buffer_size not in BUFFER_SIZES:
            errors.append("Buffer size must be one of 16/32/64/128/256 KB")
        if not 1 <= float(self.connect_timeout) <= 120:
            errors.append("Connect timeout must be between 1 and 120 seconds")
        if self.bind_mode not in BIND_MODES:
            errors.append("Binding must be Localhost or LAN")
        if self.auth_enabled and not self.username.strip():
            errors.append("Proxy auth is enabled but the username is empty")
        if self.upstream_enabled:
            if not self.upstream_host.strip():
                errors.append("Upstream proxy is enabled but the host is empty")
            if not isinstance(self.upstream_port, int) or not 1 <= self.upstream_port <= 65535:
                errors.append("Upstream port must be an integer between 1 and 65535")
            if self.upstream_kind not in ("http", "socks5"):
                errors.append("Upstream type must be HTTP CONNECT or SOCKS5")
        return errors

    # ------------------------------------------------------------ persistence
    def save(self) -> None:
        config_path().write_text(
            json.dumps(dataclasses.asdict(self), indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls) -> tuple["ProxyConfig", str | None]:
        """Load config.json; returns (config, warning-or-None)."""
        cfg = cls()
        path = config_path()
        if not path.exists():
            return cfg, None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name for f in dataclasses.fields(cls)}
            for key, value in raw.items():
                if key in known and key in cfg.__dict__:
                    current = getattr(cfg, key)
                    if isinstance(current, bool):
                        value = bool(value)
                    elif isinstance(current, int):
                        value = int(value)
                    elif isinstance(current, float):
                        value = float(value)
                    setattr(cfg, key, value)
            return cfg, None
        except (OSError, ValueError, TypeError) as exc:
            return cls(), f"{ErrorCode.CONFIG_IO} could not read config.json ({exc}) — using defaults"

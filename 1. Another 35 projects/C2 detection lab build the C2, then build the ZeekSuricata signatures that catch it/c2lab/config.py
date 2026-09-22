"""Application configuration and runtime constants."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def base_dir() -> Path:
    """Directory that should be treated as the application root.

    When frozen by PyInstaller it is the executable's folder so generated
    artifacts land next to the exe; in development it is the repo folder.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    """Folder where sessions / reports / exports are written."""
    root = base_dir()
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


APP_NAME = "C2 Detection Lab"
APP_VERSION = "1.0.0"

DEFAULT_PORT = 8080
DEFAULT_INTERVAL = 5
DEFAULT_JITTER = 20.0
DEFAULT_DURATION = 60
MAX_LOG_ROWS = 5000


@dataclass
class LabConfig:
    """Runtime configuration of a simulation session."""

    profile_name: str = "Cobalt Strike Beacon"
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    beacon_interval: int = DEFAULT_INTERVAL
    jitter: float = DEFAULT_JITTER
    duration: int = DEFAULT_DURATION
    output_dir: Path = field(default_factory=app_data_dir)

    @property
    def description(self) -> str:
        return (
            f"profile={self.profile_name} endpoint={self.host}:{self.port} "
            f"interval={self.beacon_interval}s jitter={self.jitter}% "
            f"duration={self.duration}s"
        )


def first_free_port(preferred: int, host: str = "127.0.0.1") -> int:
    """Return *preferred* if it is free, otherwise a nearby free port."""
    import socket

    tried = set()
    for port in range(preferred, preferred + 50):
        if port in tried:
            continue
        tried.add(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return preferred
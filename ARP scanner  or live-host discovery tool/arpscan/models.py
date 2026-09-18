"""Core data model for discovered hosts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Host:
    """A live host discovered on the local network segment.

    Attributes:
        ip: IPv4 address as a string.
        mac: MAC address in ``aa:bb:cc:dd:ee:ff`` (lowercase) form.
        vendor: Optional OUI-derived vendor name, filled in by the scanner
            when vendor lookup is enabled.
    """

    ip: str
    mac: str
    vendor: Optional[str] = None

    def to_dict(self) -> dict:
        """Plain dict suitable for JSON/CSV serialization."""
        return {"ip": self.ip, "mac": self.mac, "vendor": self.vendor or ""}
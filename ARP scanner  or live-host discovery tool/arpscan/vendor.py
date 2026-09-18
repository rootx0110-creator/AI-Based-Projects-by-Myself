"""OUI vendor lookup for MAC addresses.

Ships with a small sample database of well-known OUIs so the tool is useful
out of the box. For full coverage, download the IEEE OUI list and point the
``--vendor-db`` flag at it. The file format is one record per line::

    A42BB0  Dell Inc.
    # lines starting with '#' are comments
"""

from __future__ import annotations

from typing import Dict, Optional

from .arp_parse import normalize_mac

# (first 3 bytes, uppercased, no separators) -> vendor
OUI_DB: Dict[str, str] = {
    "000C29": "VMware",
    "005056": "VMware",
    "001C42": "VMware",
    "00037F": "Cisco",
    "000E83": "Cisco",
    "001F26": "Cisco",
    "0050B6": "Cisco",
    "3C5A37": "Dell",
    "A42BB0": "Dell",
    "001D09": "Dell",
    "001B21": "Intel",
    "0026AB": "Intel",
    "0050B2": "Intel",
    "F8B156": "Intel",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Foundation",
    "E45F01": "Raspberry Pi Foundation",
    "3CD92B": "Raspberry Pi Foundation",
    "0024BE": "Apple",
    "3C15C2": "Apple",
    "ACBC32": "Apple",
    "F0D5BF": "Apple",
    "0090D0": "D-Link",
    "0013CE": "D-Link",
    "AC84C6": "D-Link",
    "0004ED": "ASUSTek",
    "001E8C": "ASUSTek",
    "D8BB2C": "ASUSTek",
    "001C25": "Hewlett Packard",
    "A0D3C1": "Hewlett Packard",
    "98E7F5": "Hewlett Packard",
    "002590": "TP-Link",
    "50C7BF": "TP-Link",
    "E8DE27": "TP-Link",
    "A4F4B2": "TP-Link",
    "001111": "Netgear",
    "204E7F": "Netgear",
    "2409F4": "Netgear",
    "00161C": "Aruba Networks",
    "0C8BFD": "Aruba Networks",
    "009B90": "Huawei",
    "F84C06": "Huawei",
    "FC733C": "Huawei",
    "00E04C": "Realtek",
    "52A4AA": "Realtek",
    "EC8EAE": "Realtek",
    "F4F15A": "Amazon Technologies",
    "00BB3A": "Amazon Technologies",
    "5886FA": "Samsung",
    "F00113": "Samsung",
    "001A11": "Google",
    "D4F46F": "Google",
    "485AB6": "Google",
    "008C10": "Roku",
    "04A151": "Sonos",
    "000F3D": "Sonos",
    "78E3B5": "Sony",
    "A4D18F": "Nintendo",
    "DC0EA1": "Nintendo",
    "80B686": "Xerox",
    "000AF7": "Microsoft",
    "0050F2": "Microsoft",
    "28C2DD": "Microsoft",
}


def load_vendor_db(path: str) -> Dict[str, str]:
    """Load a custom OUI database from a file.

    Each non-comment line is ``PREFIX VENDOR`` where prefix is 6 hex digits.
    """
    db: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            prefix, vendor = parts
            db[prefix.upper().replace(":", "").replace("-", "")] = vendor
    return db


def lookup_vendor(mac: str, db: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Return the vendor for a MAC address, or ``None`` if unknown."""
    mac_norm = normalize_mac(mac).replace(":", "")
    prefix = mac_norm[:6].upper()
    return (db if db is not None else OUI_DB).get(prefix)
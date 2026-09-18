"""Command-line interface for arpscan."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from . import __version__
from .backends import BackendError
from .localnet import detect_local_networks
from .output import format_hosts
from .scanner import Scanner, select_backend
from .vendor import load_vendor_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arpscan",
        description=(
            "ARP scanner / live-host discovery tool. Discovers which IPs on a "
            "local network segment respond (and their MAC addresses)."
        ),
        epilog=(
            "Examples:\n"
            "  arpscan 192.168.1.0/24\n"
            "  arpscan 192.168.1.10-192.168.1.50 --format json\n"
            "  arpscan --auto\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="TARGET",
        help=(
            "networks/ranges/hosts to scan, e.g. 192.168.1.0/24, "
            "192.168.1.10-50, or 192.168.1.1 (comma or space separated)"
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="auto-detect the local network(s) and scan them",
    )
    parser.add_argument(
        "-b",
        "--backend",
        choices=("auto", "scapy", "system"),
        default="auto",
        help=(
            "probe strategy: scapy (raw ARP, needs scapy + privileges), "
            "system (ping sweep + OS ARP table, no deps), auto (default)"
        ),
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=2.0,
        help="seconds to wait for a response (default: 2.0)",
    )
    parser.add_argument(
        "-r",
        "--retries",
        type=int,
        default=1,
        help="extra probe attempts per target for the scapy backend (default: 1)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "json", "csv"),
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--no-vendor",
        action="store_true",
        help="skip OUI vendor lookup",
    )
    parser.add_argument(
        "--vendor-db",
        metavar="FILE",
        help="custom OUI database file ('PREFIX VENDOR' per line)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print progress and backend choice to stderr",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"arpscan {__version__}",
    )
    return parser


def _log(verbose: bool, message: str) -> None:
    if verbose:
        print(f"[arpscan] {message}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.targets and not args.auto:
        parser.error("provide at least one TARGET or use --auto")

    if args.auto:
        networks = detect_local_networks()
        if not networks:
            print(
                "error: could not detect a local network (try passing a target "
                "explicitly)",
                file=sys.stderr,
            )
            return 1
        targets: List[str] = [str(net) for net in networks]
        _log(args.verbose, f"auto-detected network(s): {', '.join(targets)}")
    else:
        targets = list(args.targets)

    vendor_db = load_vendor_db(args.vendor_db) if args.vendor_db else None

    chosen = args.backend
    if chosen == "auto":
        backend = select_backend("auto")
        _log(args.verbose, f"backend: {backend.name}")
        try:
            hosts = Scanner(backend, vendor_db, do_vendor=not args.no_vendor).scan(
                targets, timeout=args.timeout, retries=args.retries
            )
        except BackendError:
            # e.g. scapy present but no raw-packet privileges: fall back.
            fallback = select_backend("system")
            _log(args.verbose, f"backend {backend.name} failed; retrying with {fallback.name}")
            hosts = Scanner(fallback, vendor_db, do_vendor=not args.no_vendor).scan(
                targets, timeout=args.timeout, retries=args.retries
            )
    else:
        backend = select_backend(chosen)
        _log(args.verbose, f"backend: {backend.name}")
        try:
            hosts = Scanner(backend, vendor_db, do_vendor=not args.no_vendor).scan(
                targets, timeout=args.timeout, retries=args.retries
            )
        except BackendError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    sys.stdout.write(format_hosts(hosts, args.format))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
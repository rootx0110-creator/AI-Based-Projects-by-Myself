"""Command-line interface (headless, CI friendly)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core.contexts import make_context
from .core.models import Profile
from .core.scanner import Scanner, load_rules
from .core.exceptions import HardeningError
from .reporting import render_html, render_pdf


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hardening-checker",
        description="Read-only CIS-style endpoint hardening audit.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    s_scan = sub.add_parser("scan", help="run a compliance scan")
    s_scan.add_argument("--profile", choices=["l1", "l2"], default="l1",
                        help="benchmark profile (default: l1)")
    s_scan.add_argument("--json", metavar="PATH", help="write machine-readable JSON")
    s_scan.add_argument("--html", metavar="PATH", help="write HTML report")
    s_scan.add_argument("--pdf", metavar="PATH", help="write PDF report")
    s_scan.add_argument("--no-manual", action="store_true",
                        help="exclude manual-review rules")
    s_scan.add_argument("--no-info", action="store_true",
                        help="exclude informational rules")
    s_scan.add_argument("--quiet", action="store_true", help="suppress progress output")

    s_rules = sub.add_parser("rules", help="list rules for this platform")
    s_rules.add_argument("--profile", choices=["l1", "l2"], default=None)

    return p


def _print_progress(rule_id: str, current: int, total: int) -> None:
    if not sys.stdout.isatty():
        return
    width = 28
    filled = int(width * current / max(total, 1))
    bar = "#" * filled + "-" * (width - filled)
    sys.stdout.write(f"\r[{bar}] {current}/{total} {rule_id:<20}")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def cmd_scan(args: argparse.Namespace) -> int:
    profile = Profile.L2 if args.profile == "l2" else Profile.L1
    scanner = Scanner(
        context=make_context(),
        progress=None if args.quiet else _print_progress,
    )
    report = scanner.scan(
        profile=profile,
        include_manual=not args.no_manual,
        include_info=not args.no_info,
    )

    s = report.summary
    print(f"\nScan {report.scan_id} on {report.platform.hostname}")
    print(f"Profile: {report.profile}  Score: {report.score:.1f}%  Grade: {report.grade}")
    print(f"Passed {s.passed} / {s.total}  (failed {s.failed}, errors {s.errors}, "
          f"skipped {s.skipped + s.not_applicable}, manual {s.manual})")

    # Write outputs defensively: a bad path must never turn into a traceback.
    failures = 0
    try:
        if args.json:
            json_path = Path(args.json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(report.to_dict(), indent=2, default=str),
                encoding="utf-8")
            print(f"JSON written: {json_path}")
        if args.html:
            out = render_html(report, args.html)
            print(f"HTML written: {out}")
        if args.pdf:
            out = render_pdf(report, args.pdf)
            print(f"PDF written: {out}")
    except OSError as exc:
        print(f"error: cannot write output file: {exc}", file=sys.stderr)
        failures = 1

    # Exit codes: 0 = fully compliant, 1 = failures / output error
    if failures:
        return 2
    return 0 if s.failed == 0 and s.errors == 0 else 1


def cmd_rules(args: argparse.Namespace) -> int:
    ctx = make_context()
    rules = load_rules(ctx.name)
    if args.profile:
        prof = Profile.L2 if args.profile == "l2" else Profile.L1
        rules = [r for r in rules if r.profile is prof]
    print(f"{len(rules)} rules for platform '{ctx.name}':\n")
    for r in rules:
        flag = " [manual]" if r.manual else ""
        print(f"  {r.rule_id:<14} {r.severity.value:<9} [{r.profile.value}] "
              f"{r.title}{flag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "scan":
            return cmd_scan(args)
        if args.cmd == "rules":
            return cmd_rules(args)
    except HardeningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\naborted", file=sys.stderr)
        return 130
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

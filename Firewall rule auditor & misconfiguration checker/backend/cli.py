"""Headless / CI audit runner.

Examples:
    python backend/cli.py audit samples/iptables.txt --format iptables --json out.json
    python backend/cli.py audit samples --all-formats --json reports/all.json
    python backend/cli.py formats
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

try:
    from .engine import FORMATS, audit
except ImportError:  # allow `python backend/cli.py ...`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.engine import FORMATS, audit


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="framc", description="Firewall Rule Auditor & Misconfiguration Checker")
    sub = parser.add_subparsers(dest="cmd")

    fmt_p = sub.add_parser("formats", help="list supported formats")
    fmt_p.add_argument("--json", action="store_true")

    audit_p = sub.add_parser("audit", help="audit a config file")
    audit_p.add_argument("path", nargs="+", help="file or directory")
    audit_p.add_argument("--format", choices=list(FORMATS), default=None,
                         help="vendor format (auto-guessed per file if omitted)")
    audit_p.add_argument("--json", default=None, help="write report JSON to file")
    audit_p.add_argument("--all-formats", action="store_true",
                         help="run every parser on every file (sanity mode)")

    args = parser.parse_args(argv)
    if args.cmd == "formats":
        if args.json:
            print(json.dumps(FORMATS, indent=2))
        else:
            for k, v in FORMATS.items():
                print(f"{k:<12} {v}")
        return 0

    if args.cmd != "audit":
        parser.print_help()
        return 2

    failures = 0
    outputs = []
    for path in args.path:
        if os.path.isdir(path):
            files = sorted(glob.glob(os.path.join(path, "*")))
        else:
            files = [path]

        jobs = []
        if args.all_formats:
            for f in files:
                for fmt in FORMATS:
                    jobs.append((f, fmt))
        elif args.format:
            jobs = [(f, args.format) for f in files]
        else:
            jobs = [(f, [guess_format(os.path.basename(f))][0]) for f in files]

        for file, fmt in jobs:
            if not os.path.isfile(file):
                print(f"skip: {file} (not a file)")
                failures += 1
                continue
            try:
                with open(file, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError as exc:
                print(f"error reading {file}: {exc}")
                failures += 1
                continue
            report = audit(fmt, content, name=os.path.basename(file))
            outputs.append(report)
            _print_summary(os.path.basename(file), fmt, report)
            if not report["rules"]:
                failures += 1

    if args.json:
        out_path = args.json
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            payload = outputs[0] if len(outputs) == 1 else outputs
            json.dump(payload, fh, indent=2)
        print(f"\nwrote {args.json}")
    return 1 if failures else 0


def guess_format(filename: str) -> str:
    low = filename.lower()
    if "iptable" in low or low.startswith("ipt"):
        return "iptables"
    if "asa" in low or "cisco" in low:
        return "cisco-asa"
    if "forti" in low:
        return "fortigate"
    if "pf" in low or "pfsense" in low:
        return "pfsense"
    if "win" in low or "netsh" in low:
        return "windows"
    if "pa" in low or "palo" in low:
        return "paloalto"
    return "plain"


def _print_summary(name: str, fmt: str, report: dict) -> None:
    po = report["posture"]
    summ = report["summary"]
    print(f"\n=== {name}  [{fmt}]  posture {po['score']} ({po['grade']}) "
          f"| finding_count {summ and report['meta']['finding_count']}")
    print(f"    rules={report['meta']['rule_count']} "
          f"nat={report['meta']['nat_count']} "
          f"warnings={len(report['meta']['warnings'])}")
    for f in report["findings"]:
        print(f"    [{f['severity']:>8}] {f['id']} {f['title']}")


if __name__ == "__main__":
    sys.exit(main())
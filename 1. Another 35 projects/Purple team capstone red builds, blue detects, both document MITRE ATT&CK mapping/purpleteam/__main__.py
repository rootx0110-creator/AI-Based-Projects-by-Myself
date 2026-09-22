"""Command-line entry points for the purple team engine.

GUI:        python main.py            (or the built exe with no args)
Headless:   python main.py --cli [T1053.005,T1041]
Self-test:  python -m purpleteam.selftest
Docs:       python -m purpleteam.docs
"""

from __future__ import annotations

import argparse
import sys


def run_cli(selected: str | None) -> int:
    from . import mitre
    from .exercise import full_exercise
    from .report import open_report, save_report

    techniques = [t.strip() for t in selected.split(",")] if selected else mitre.technique_ids()
    valid = [t for t in techniques if t in mitre.technique_ids()]

    if not valid:
        print("No valid technique ids supplied. Use e.g. --cli T1053.005,T1041 or omit for all.")
        return 2

    print(f"Building red techniques: {', '.join(valid)}")
    session = full_exercise(technique_ids=valid)
    path = save_report(session)
    print(f"Exercise complete. Detection rate {session.score['detection_rate']}% "
          f"({session.score['techniques_detected']}/{session.score['techniques_executed']}).")
    print(f"Report: {path}")
    open_report(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="PurpleTeamCapstone",
                                     description="Purple team lab - red builds, blue detects, MITRE ATT&CK mapped.")
    parser.add_argument("--cli", nargs="?", const="", metavar="TECH_IDS",
                        help="headless run; optional comma-separated technique ids")
    parser.add_argument("--selftest", action="store_true", help="run engine self-test")
    parser.add_argument("--docs", action="store_true", help="regenerate docs/*.md")
    args = parser.parse_args(argv)

    if args.selftest:
        from .selftest import run as st_run
        return st_run()
    if args.docs:
        from .docs import main as docs_main
        docs_main()
        return 0
    if args.cli is not None:
        return run_cli(args.cli or None)

    from .app import run_gui
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
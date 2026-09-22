"""Headless self-test: builds a full exercise, verifies scoring invariants and
report generation.   Exit code 0 = all good.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import mitre
from .exercise import full_exercise
from .report import build_report


def run() -> int:
    failures: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ptc_selftest_"))
    lab = tmp / "lab_target"

    s = full_exercise(technique_ids=mitre.technique_ids(), lab_root=lab, reset=True, save=False)

    expect = {
        "techniques_executed": len(mitre.RED_TECHNIQUES),
        "findings_count": ">0",
        "detection_rate": 100.0,
    }
    for key, want in expect.items():
        got = s.score.get(key)
        if want == ">0":
            ok = bool(got and got > 0)
        else:
            ok = got == want
        if not ok:
            failures.append(f"score.{key} = {got!r}, expected {want!r}")

    total_tech = set(mitre.technique_ids())
    if not set(s.techniques_executed) <= total_tech:
        failures.append("executed techniques not subset of registry")

    for tid, row in s.score["matrix"].items():
        fired = [r for r, v in row.items() if v]
        if not fired:
            failures.append(f"technique {tid} has no fired rule")

    html = build_report(s)
    for token in ("ATT&amp;CK Coverage Matrix", "Executive Summary", "</html>"):
        if token not in html:
            failures.append(f"report missing {token!r}")
    if "<style>" not in html:
        failures.append("report missing inline CSS")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"SELFTEST PASSED - {s.score['techniques_executed']} techniques, "
          f"{s.score['findings_count']} findings, {len(s.score['matrix'])} matrix rows.")
    return 0


def main() -> int:
    import sys
    sys.exit(run())


if __name__ == "__main__":
    main()
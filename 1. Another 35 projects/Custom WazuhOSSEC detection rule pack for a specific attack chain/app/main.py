"""RulePackStudio entry point.

GUI mode (default):           python main.py
CLI smoke mode:               python main.py --cli
"""
from __future__ import annotations

import os
import sys


def _run_cli() -> int:
    from app import rules_core as core
    from app import report
    from app.rules_library import library_rules

    pack = core.RulePack()
    pack.load_library(library_rules())
    issues = pack.validate()
    print(f"[CLI] loaded {pack.total} rules, {pack.stages_covered}/{len(core.STAGES)} stages")
    if issues:
        print("[CLI] validation issues:")
        for i in issues[:10]:
            print("  -", i)
        return 1
    print("[CLI] validation OK")
    _, export_dir, xml_path = core.default_data_paths()
    os.makedirs(export_dir, exist_ok=True)
    out = {
        "pack": os.path.join(export_dir, "rulepack_full.html"),
        "matrix": os.path.join(export_dir, "coverage_matrix.html"),
        "severity": os.path.join(export_dir, "severity_report.html"),
        "single": os.path.join(export_dir, "rule_100001.html"),
    }
    pack.export_xml(xml_path)
    with open(out["pack"], "w", encoding="utf-8") as f:
        f.write(report.generate_pack_report(pack))
    with open(out["matrix"], "w", encoding="utf-8") as f:
        f.write(report.generate_matrix_report(pack))
    with open(out["severity"], "w", encoding="utf-8") as f:
        f.write(report.generate_severity_report(pack))
    with open(out["single"], "w", encoding="utf-8") as f:
        f.write(report.generate_single_rule_report(pack, 100001))
    print(f"[CLI] xml  -> {xml_path}")
    for k, p in out.items():
        print(f"[CLI] html -> {p} ({os.path.getsize(p)} bytes)")
    return 0


def _run_gui() -> int:
    from app.ui import theme
    from app.ui.app import MainApp

    theme.init()
    app = MainApp()
    app.mainloop()
    return 0


def main() -> int:
    if "--cli" in sys.argv:
        return _run_cli()
    return _run_gui()


if __name__ == "__main__":
    sys.exit(main())
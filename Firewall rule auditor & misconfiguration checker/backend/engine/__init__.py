"""Analysis engine: parse → detect → score → report."""

from __future__ import annotations

from typing import Dict, List, Optional

from .parsers import FORMATS, parse
from .detectors import scan
from .scoring import build_report


def audit(fmt: str, content: str, name: str = "config") -> Dict:
    """Full audit pipeline. Returns a report envelope dict.

    Never raises for content issues: parse warnings are captured and returned.
    """
    result = parse(fmt, content)
    findings = scan(result.rules, result.nat_rules)
    return build_report(
        name=name, fmt=fmt, rules=result.rules,
        nat_rules=result.nat_rules, findings=findings,
        warnings=result.warnings,
    )


__all__ = ["FORMATS", "parse", "scan", "audit", "build_report"]
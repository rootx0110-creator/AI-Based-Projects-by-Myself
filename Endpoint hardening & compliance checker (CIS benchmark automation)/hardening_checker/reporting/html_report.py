"""HTML report generation."""

from __future__ import annotations

import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from .. import __version__
from ..core.exceptions import ReportError
from ..core.models import CheckResult, ResultStatus, ScanReport
from .templates_env import make_env


def build_context(report: ScanReport) -> dict:
    """Aggregate report data into a template-friendly context dict."""
    results: list[CheckResult] = report.results
    summary = report.summary

    severity_stats = defaultdict(int)
    for res in results:
        severity_stats[res.severity.value] += 1

    cat_totals: dict[str, int] = defaultdict(int)
    cat_passed: dict[str, int] = defaultdict(int)
    cat_failed: dict[str, int] = defaultdict(int)
    for res in results:
        cat_totals[res.rule.category] += 1
        if res.status is ResultStatus.PASS:
            cat_passed[res.rule.category] += 1
        elif res.status is ResultStatus.FAIL:
            cat_failed[res.rule.category] += 1

    category_stats = []
    for cat in sorted(cat_totals):
        total = cat_totals[cat]
        rate = round(cat_passed[cat] * 100 / total, 1) if total else 0.0
        category_stats.append({
            "category": cat,
            "total": total,
            "passed": cat_passed[cat],
            "failed": cat_failed[cat],
            "rate": rate,
        })

    remediations = {
        r.rule.rule_id: r.rule.remediation
        for r in results
        if r.rule.remediation is not None
    }

    # Flatten results into simple row objects for the template
    # (rule fields + result fields on one namespace).
    rows = []
    for r in sorted(results, key=_result_sort_key):
        rows.append(SimpleNamespace(
            rule_id=r.rule.rule_id,
            title=r.rule.title,
            severity=r.severity.value,
            category=r.rule.category,
            profile=r.rule.profile.value,
            status=r.status.value,
            message=r.message,
            evidence=r.evidence,
            observed=r.observed,
            expected=r.expected,
        ))

    return {
        "report": report,
        "platform": report.platform,
        "summary": summary,
        "results": rows,
        "severity_stats": dict(severity_stats),
        "category_stats": category_stats,
        "remediations": remediations,
        "app_version": __version__,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def render_html(report: ScanReport, out_path: str | Path, open_browser: bool = False) -> Path:
    """Render a ScanReport to a self-contained HTML file."""
    out = Path(out_path)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        env = make_env()
        template = env.get_template("base.html.j2")
        html_text = template.render(**build_context(report))
        out.write_text(html_text, encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"cannot write HTML report: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface template errors cleanly
        raise ReportError(f"HTML rendering failed: {exc!r}") from exc

    if open_browser:
        webbrowser.open(out.as_uri())
    return out


def _result_sort_key(res: CheckResult):
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    st_order = {"fail": 0, "error": 1, "manual": 2, "skipped": 3,
                "not_applicable": 4, "pass": 5}
    return (
        st_order.get(res.status.value, 9),
        sev_order.get(res.severity.value, 9),
        res.rule.category,
        res.rule.rule_id,
    )


__all__ = ["render_html", "build_context"]

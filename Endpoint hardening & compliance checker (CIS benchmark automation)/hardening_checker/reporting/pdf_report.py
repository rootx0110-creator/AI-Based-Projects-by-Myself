"""PDF report generation (ReportLab, pure Python - no external binaries)."""

from __future__ import annotations

import html as _html
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import __version__
from ..core.exceptions import ReportError
from ..core.models import CheckResult, ResultStatus, ScanReport

SEV_COLORS = {
    "critical": colors.HexColor("#e11d48"),
    "high": colors.HexColor("#ea580c"),
    "medium": colors.HexColor("#ca8a04"),
    "low": colors.HexColor("#0284c7"),
    "info": colors.HexColor("#2563eb"),
}

STATUS_COLORS = {
    "pass": colors.HexColor("#059669"),
    "fail": colors.HexColor("#dc2626"),
    "error": colors.HexColor("#d97706"),
    "skipped": colors.HexColor("#64748b"),
    "not_applicable": colors.HexColor("#64748b"),
    "manual": colors.HexColor("#2563eb"),
}

STATUS_LABELS = {
    "pass": "PASS",
    "fail": "FAIL",
    "error": "ERROR",
    "skipped": "SKIPPED",
    "not_applicable": "N/A",
    "manual": "MANUAL",
}

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
ST_ORDER = {"fail": 0, "error": 1, "manual": 2, "skipped": 3,
            "not_applicable": 4, "pass": 5}


def render_pdf(report: ScanReport, out_path: str | Path) -> Path:
    """Render a ScanReport to a paginated PDF."""
    out = Path(out_path)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(out), pagesize=A4,
            leftMargin=16 * mm, rightMargin=16 * mm,
            topMargin=18 * mm, bottomMargin=16 * mm,
            title=f"Compliance Report {report.scan_id}",
            author=f"Hardening Checker v{__version__}",
        )
        doc.build(_story(report))
        return out
    except ReportError:
        raise
    except OSError as exc:
        raise ReportError(f"cannot write PDF report: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ReportError(f"PDF rendering failed: {exc!r}") from exc


# --------------------------------------------------------------------------- #
# Story construction
# --------------------------------------------------------------------------- #
def _story(report: ScanReport) -> list:
    results = sorted(report.results, key=_sort_key)
    summary = report.summary
    styles = getSampleStyleSheet()

    title_s = ParagraphStyle(
        "RTitle", parent=styles["Title"], fontSize=19, leading=23,
        textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    sub_s = ParagraphStyle(
        "RSub", parent=styles["Normal"], fontSize=9.5, leading=13,
        textColor=colors.HexColor("#475569"),
    )
    h2_s = ParagraphStyle(
        "RH2", parent=styles["Heading2"], fontSize=12.5, leading=16,
        textColor=colors.HexColor("#0e7490"), spaceBefore=14, spaceAfter=6,
    )
    body_s = ParagraphStyle(
        "RBody", parent=styles["Normal"], fontSize=9, leading=12.5,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_s = ParagraphStyle(
        "RCell", parent=styles["Normal"], fontSize=8, leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_bold = ParagraphStyle("RCellB", parent=cell_s, fontName="Helvetica-Bold")
    cell_mut = ParagraphStyle(
        "RCellM", parent=cell_s, fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#64748b"),
    )
    mono_s = ParagraphStyle(
        "RMono", parent=cell_s, fontName="Courier", fontSize=7, leading=9,
        textColor=colors.HexColor("#155e75"), backColor=colors.HexColor("#f1f5f9"),
        borderPadding=3, spaceBefore=3,
    )

    story: list = []

    # ------------------------------------------------------------- cover
    story.append(Paragraph("Endpoint Hardening &amp; Compliance Checker", title_s))
    story.append(Paragraph(
        "CIS-style benchmark assessment &middot; read-only audit "
        f"&middot; generated {datetime.now():%Y-%m-%d %H:%M} by v{__version__}",
        sub_s))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#e2e8f0")))

    p = report.platform
    story.append(Paragraph(p.hostname, ParagraphStyle(
        "Host", parent=title_s, fontSize=15, spaceBefore=10)))

    meta_rows = [
        ["Operating system", f"{p.os_name} {p.os_version}" + (f" (build {p.build})" if p.build else "")],
        ["Architecture", p.arch],
        ["Profile", report.profile.replace("_", " ").upper()],
        ["Scan ID", report.scan_id],
        ["Started / finished", f"{report.started_at}  \u2192  {report.finished_at}"
         f"  ({report.duration_seconds:.1f}s)"],
        ["Elevation", "Elevated (admin)" if p.is_admin else "Non-elevated"],
        ["Domain joined", "Yes" if p.domain_joined else "No"],
        ["IP addresses", ", ".join(p.ip_addresses) or "n/a"],
    ]
    if p.extra:
        for k, v in list(p.extra.items())[:4]:
            meta_rows.append([k.replace("_", " ").title(), v])

    meta_table = Table(
        [[Paragraph(f"<b>{_e(a)}</b>", cell_s), Paragraph(_e(b), cell_s)]
         for a, b in meta_rows],
        colWidths=[45 * mm, 115 * mm], hAlign="LEFT",
    )
    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)

    # ------------------------------------------------------------ score
    score_color = (colors.HexColor("#059669") if report.score >= 80
                   else colors.HexColor("#d97706") if report.score >= 60
                   else colors.HexColor("#dc2626"))
    score_table = Table(
        [[
            Paragraph(f"<font size=28 color=#{score_color.hexval()[2:]}>"
                      f"<b>{report.score:.1f}%</b></font>", cell_s),
            Paragraph(f"<font size=18 color=#{score_color.hexval()[2:]}><b>"
                      f"Grade {report.grade}</b></font><br/>"
                      f"<font size=8 color=#64748b>{summary.passed} of {summary.total} "
                      f"checks passed</font>", cell_s),
            Paragraph(
                f"<font size=8><b>Passed</b> {summary.passed}</font><br/>"
                f"<font size=8><b>Failed</b> {summary.failed}</font><br/>"
                f"<font size=8><b>Errors</b> {summary.errors}</font><br/>"
                f"<font size=8><b>N/A + skipped</b> "
                f"{summary.not_applicable + summary.skipped}</font><br/>"
                f"<font size=8><b>Manual</b> {summary.manual}</font>", cell_s),
        ]],
        colWidths=[52 * mm, 54 * mm, 54 * mm], hAlign="LEFT",
    )
    score_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(Spacer(1, 10))
    story.append(score_table)

    # -------------------------------------------------------- severity mix
    sev_counts: dict[str, int] = defaultdict(int)
    for res in results:
        sev_counts[res.severity.value] += 1

    sev_rows = [[Paragraph("<b>Severity</b>", cell_s),
                 Paragraph("<b>Failed</b>", cell_s),
                 Paragraph("<b>Total</b>", cell_s)]]
    for sev in ("critical", "high", "medium", "low", "info"):
        total_sev = sum(1 for r in results if r.severity.value == sev)
        failed_sev = sum(
            1 for r in results
            if r.severity.value == sev and r.status is ResultStatus.FAIL
        )
        sev_rows.append([
            Paragraph(f"<font color=#{SEV_COLORS[sev].hexval()[2:]}><b>{sev.upper()}</b></font>", cell_s),
            Paragraph(str(failed_sev), cell_s),
            Paragraph(str(total_sev), cell_s),
        ])
    sev_table = Table(sev_rows, colWidths=[40 * mm, 30 * mm, 30 * mm], hAlign="LEFT")
    sev_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Paragraph("Findings by severity", h2_s))
    story.append(sev_table)

    # ------------------------------------------------------------ category
    cat_total: dict[str, int] = defaultdict(int)
    cat_pass: dict[str, int] = defaultdict(int)
    cat_fail: dict[str, int] = defaultdict(int)
    for res in results:
        cat_total[res.rule.category] += 1
        if res.status is ResultStatus.PASS:
            cat_pass[res.rule.category] += 1
        elif res.status is ResultStatus.FAIL:
            cat_fail[res.rule.category] += 1

    cat_rows = [[Paragraph("<b>Category</b>", cell_s),
                 Paragraph("<b>Total</b>", cell_s),
                 Paragraph("<b>Passed</b>", cell_s),
                 Paragraph("<b>Failed</b>", cell_s),
                 Paragraph("<b>Rate</b>", cell_s)]]
    for cat in sorted(cat_total):
        t, pa = cat_total[cat], cat_pass[cat]
        rate = pa * 100 / t if t else 0
        cat_rows.append([
            Paragraph(_e(cat), cell_s),
            Paragraph(str(t), cell_s),
            Paragraph(f'<font color="#059669">{pa}</font>', cell_s),
            Paragraph(f'<font color="#dc2626">{cat_fail[cat]}</font>', cell_s),
            Paragraph(f"{rate:.0f}%", cell_s),
        ])
    cat_table = Table(cat_rows, colWidths=[80 * mm, 20 * mm, 22 * mm, 22 * mm, 20 * mm],
                      hAlign="LEFT", repeatRows=1)
    cat_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Paragraph("Category breakdown", h2_s))
    story.append(cat_table)

    # ----------------------------------------------------------- findings
    story.append(PageBreak())
    story.append(Paragraph("Findings", h2_s))

    current_status: str | None = None
    for res in results:
        st = res.status.value
        if st != current_status:
            current_status = st
            label = STATUS_LABELS.get(st, st.upper())
            color = STATUS_COLORS.get(st, colors.black)
            story.append(Paragraph(
                f'<font color="{color.hexval().replace("0x", "#")}"><b>{label}</b></font>'
                f' <font size=8 color="#64748b">'
                f'({sum(1 for r in results if r.status.value == st)} items)</font>',
                ParagraphStyle("Sec", parent=h2_s, fontSize=10.5, spaceBefore=10,
                               spaceAfter=4)))

        rule = res.rule
        sev_color = SEV_COLORS[rule.severity.value]
        st_color = STATUS_COLORS.get(st, colors.black)

        head_left = Paragraph(
            f'<font color="{sev_color.hexval().replace("0x", "#")}">'
            f'<b>{rule.severity.value.upper()}</b></font> '
            f'<font size=7.5 color="#64748b">{_e(rule.rule_id)} \u00b7 '
            f'{_e(rule.category)}</font><br/>'
            f"<b>{_e(rule.title)}</b>", cell_s)
        head_right = Paragraph(
            f'<b>{STATUS_LABELS.get(st, st.upper())}</b>',
            ParagraphStyle(
                "St", parent=cell_s, alignment=2,
                textColor=st_color))

        row = Table([[head_left, head_right]], colWidths=[130 * mm, 46 * mm])
        row.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fafafa")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        inner: list = [row]

        if res.message:
            inner.append(Paragraph(_e(res.message), cell_mut))
        if res.status is ResultStatus.FAIL and rule.remediation:
            rem = rule.remediation
            rem_text = f"<b>Remediation:</b> {_e(rem.summary)}"
            if rem.steps:
                rem_text += "<br/>" + "<br/>".join(
                    f"\u2022 {_e(s)}" for s in rem.steps)
            if rem.script:
                rem_text += f"<br/>{_e(rem.script)}"
            inner.append(Paragraph(rem_text, mono_s))
        if res.evidence:
            for e in res.evidence[:3]:
                raw = (e.raw or "").strip()
                if raw:
                    inner.append(Paragraph(
                        f"<i> Evidence ({_e(e.source)}):</i> "
                        f"{_e(raw[:400])}", cell_mut))

        block = Table([[item] for item in inner], colWidths=[176 * mm])
        block.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(KeepTogether(block))

    # ------------------------------------------------------------ footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#e2e8f0")))
    story.append(Paragraph(
        f"Generated {datetime.now():%Y-%m-%d %H:%M:%S} \u00b7 "
        f"Endpoint Hardening &amp; Compliance Checker v{__version__} \u00b7 "
        "Read-only assessment \u2014 no system settings were modified during this scan.",
        cell_mut))

    return story


def _e(text) -> str:
    """Escape text for ReportLab paragraph markup."""
    return _html.escape(str(text), quote=False)


def _sort_key(res: CheckResult):
    return (
        ST_ORDER.get(res.status.value, 9),
        SEV_ORDER.get(res.severity.value, 9),
        res.rule.category,
        res.rule.rule_id,
    )


__all__ = ["render_pdf"]

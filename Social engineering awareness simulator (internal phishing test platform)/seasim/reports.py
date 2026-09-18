"""Reporting for SeaSim: aggregates, CSV exports, and text reports.

Aggregation is deliberately simple and inspectable - counts of the four
coarse outcomes per campaign/department, plus susceptibility rates. No
per-person drill-down beyond interaction status is provided by design
(data minimization).
"""

from __future__ import annotations

import csv
import html
import io
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from seasim.engine import models as M
from seasim.engine.engine import Engine


@dataclass
class CampaignStats:
    campaign_id: str
    name: str
    status: str
    template_name: str
    template_difficulty: str
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    reported: int = 0
    dismissed: int = 0
    trained: int = 0
    avg_risk: float = 0.0

    @property
    def click_rate(self) -> float:
        return (self.clicked / self.sent * 100.0) if self.sent else 0.0

    @property
    def open_rate(self) -> float:
        return (self.opened / self.sent * 100.0) if self.sent else 0.0

    @property
    def report_rate(self) -> float:
        return (self.reported / self.sent * 100.0) if self.sent else 0.0

    @property
    def resilience(self) -> float:
        """Share of sent emails that were reported or dismissed untouched."""
        if not self.sent:
            return 0.0
        return (self.reported + self.dismissed) / self.sent * 100.0


def campaign_stats(engine: Engine, cid: str) -> Optional[CampaignStats]:
    camp = engine.get_campaign(cid)
    if camp is None:
        return None
    tpl = engine.get_template(camp.template_id)
    st = CampaignStats(
        campaign_id=cid, name=camp.name, status=camp.status,
        template_name=tpl.name if tpl else "(missing template)",
        template_difficulty=tpl.difficulty if tpl else "?",
    )
    scores: List[int] = []
    for e in engine.campaign_events(cid):
        st.sent += 1
        if e.status == M.ST_OPENED:
            st.opened += 1
        elif e.status == M.ST_CLICKED:
            st.clicked += 1
        elif e.status == M.ST_REPORTED:
            st.reported += 1
        elif e.status == M.ST_DISMISSED:
            st.dismissed += 1
        if e.trained_at:
            st.trained += 1
        if e.risk_score:
            scores.append(e.risk_score)
    st.avg_risk = round(sum(scores) / len(scores), 1) if scores else 0.0
    return st


def department_breakdown(engine: Engine, cid: str) -> List[Dict[str, object]]:
    """Per-department: sent/clicked/reported + click rate."""
    camp = engine.get_campaign(cid)
    if camp is None:
        return []
    agg: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"sent": 0, "clicked": 0, "reported": 0, "opened": 0,
                 "dismissed": 0})
    for e in engine.campaign_events(cid):
        p = engine.get_participant(e.participant_id)
        dept = p.department if p else "Unknown"
        a = agg[dept]
        a["sent"] += 1
        if e.status == M.ST_CLICKED:
            a["clicked"] += 1
        elif e.status == M.ST_REPORTED:
            a["reported"] += 1
        elif e.status == M.ST_OPENED:
            a["opened"] += 1
        elif e.status == M.ST_DISMISSED:
            a["dismissed"] += 1
    rows: List[Dict[str, object]] = []
    for dept, a in sorted(agg.items()):
        rate = (a["clicked"] / a["sent"] * 100.0) if a["sent"] else 0.0
        rows.append({"department": dept, **a, "click_rate": round(rate, 1)})
    rows.sort(key=lambda r: (-float(r["click_rate"]), str(r["department"])))
    return rows


def program_totals(engine: Engine) -> Dict[str, float]:
    """Aggregate across all non-draft campaigns."""
    tot: Dict[str, float] = {"campaigns": 0, "sent": 0, "opened": 0,
                             "clicked": 0, "reported": 0, "dismissed": 0,
                             "trained": 0}
    for c in engine.store.campaigns.values():
        if c.status == M.CAMPAIGN_DRAFT:
            continue
        st = campaign_stats(engine, c.id)
        if st is None:
            continue
        tot["campaigns"] += 1
        for k in ("sent", "opened", "clicked", "reported", "dismissed",
                  "trained"):
            tot[k] += getattr(st, k)
    sent = tot["sent"]
    tot["click_rate"] = round(tot["clicked"] / sent * 100, 1) if sent else 0.0
    tot["report_rate"] = (round(tot["reported"] / sent * 100, 1)
                          if sent else 0.0)
    return tot


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def events_csv(engine: Engine, cid: str) -> str:
    """Per-event CSV for the campaign (coarse data only)."""
    camp = engine.get_campaign(cid)
    if camp is None:
        return ""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["campaign", "participant", "email", "department", "location",
                "status", "opened_at", "clicked_at", "reported_at",
                "dismissed_at", "trained_at", "risk_score"])
    for e in engine.campaign_events(cid):
        p = engine.get_participant(e.participant_id)
        w.writerow([
            camp.name,
            p.name if p else "?",
            p.email if p else "?",
            p.department if p else "?",
            p.location if p else "?",
            e.status,
            e.opened_at, e.clicked_at, e.reported_at, e.dismissed_at,
            e.trained_at,
            e.risk_score,
        ])
    return buf.getvalue()


def dept_csv(engine: Engine, cid: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["department", "sent", "opened", "clicked", "reported",
                "dismissed", "click_rate_pct"])
    for r in department_breakdown(engine, cid):
        w.writerow([r["department"], r["sent"], r["opened"], r["clicked"],
                    r["reported"], r["dismissed"], r["click_rate"]])
    return buf.getvalue()


def build_text_report(engine: Engine, cid: str) -> str:
    """Plain-text, boardroom-ready campaign report."""
    st = campaign_stats(engine, cid)
    if st is None:
        return "Campaign not found."
    camp = engine.get_campaign(cid)
    tpl = engine.get_template(camp.template_id)
    org = engine.store.settings.org_name
    lines: List[str] = []
    ap = lines.append
    ap("=" * 62)
    ap(f" SEA-SIM AWARENESS REPORT - {st.name}")
    ap("=" * 62)
    ap(f"Organization : {org}")
    ap(f"Campaign     : {st.name}  ({st.campaign_id})")
    ap(f"Status       : {st.status}")
    ap(f"Template     : {st.template_name} "
       f"(difficulty: {st.template_difficulty})")
    if tpl is not None:
        ap(f"Techniques   : {', '.join(tpl.techniques) or 'n/a'}")
        if tpl.category == M.CATEGORY_AI:
            ap("Content      : AI-themed (consent recorded at launch)")
    ap(f"Run          : {camp.created} -> "
       f"{camp.completed_at or '(in progress)'}")
    ap("")
    ap(" OUTCOMES")
    ap("-" * 62)
    ap(f" Sent        : {st.sent}")
    ap(f" Opened      : {st.opened}   ({st.open_rate:.1f}%)")
    ap(f" Clicked     : {st.clicked}   ({st.click_rate:.1f}%)")
    ap(f" Reported    : {st.reported}   ({st.report_rate:.1f}%)")
    ap(f" Dismissed   : {st.dismissed}")
    ap(f" Trained JIT : {st.trained}")
    ap(f" Avg risk    : {st.avg_risk:.0f}/100 (higher = more risk signaled)")
    ap("")
    ap(" RESILIENCE")
    ap("-" * 62)
    ap(f" {st.resilience:.1f}% of recipients reported or dismissed without "
       f"engaging.")
    ap("")
    ap(" BY DEPARTMENT")
    ap("-" * 62)
    ap(f" {'Department':<16}{'Sent':>6}{'Clicks':>8}{'Reps':>6}"
       f"{'Click %':>9}")
    for r in department_breakdown(engine, cid):
        ap(f" {str(r['department']):<16}{int(r['sent']):>6}"
           f"{int(r['clicked']):>8}{int(r['reported']):>6}"
           f"{float(r['click_rate']):>8.1f}%")
    ap("")
    ap(" NOTES")
    ap("-" * 62)
    ap(" Simulated exercise; no credentials or personal data collected.")
    ap(" Individual outcomes are for training purposes only.")
    ap("=" * 62)
    return "\n".join(lines)


def build_html_report(engine: Engine, cid: str) -> str:
    """Self-contained HTML report for one campaign (no external deps)."""
    st = campaign_stats(engine, cid)
    if st is None:
        return "<!DOCTYPE html><html><body><p>Campaign not found.</p></body></html>"
    camp = engine.get_campaign(cid)
    tpl = engine.get_template(camp.template_id)
    org = engine.store.settings.org_name
    e = html.escape

    tech = ", ".join(tpl.techniques) if tpl is not None else "n/a"
    ai_note = ("<p class='note'>This campaign used AI-themed content - "
               "written consent was recorded at launch.</p>"
               if tpl is not None and tpl.category == M.CATEGORY_AI else "")

    dept_rows = "\n".join(
        "<tr>"
        f"<td>{e(str(r['department']))}</td>"
        f"<td>{r['sent']}</td><td>{r['opened']}</td>"
        f"<td>{r['clicked']}</td><td>{r['reported']}</td>"
        f"<td>{r['dismissed']}</td><td>{r['click_rate']:.1f}%</td>"
        "</tr>"
        for r in department_breakdown(engine, cid))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SeaSim report - {e(st.name)}</title>
<style>
  body {{ margin: 0; font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
  header {{ background: #0f172a; color: #fff; padding: 22px 32px; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header p {{ margin: 4px 0 0; color: #94a3b8; font-size: 13px; }}
  main {{ padding: 22px 32px; max-width: 960px; }}
  .tiles {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }}
  .tile {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 18px;
                 min-width: 110px; flex: 1; }}
  .tile b {{ display: block; font-size: 24px; }}
  .tile span {{ color: #64748b; font-size: 11px; font-weight: bold; letter-spacing: .5px; }}
  .tile.clicked b {{ color: #dc2626; }} .tile.reported b {{ color: #16a34a; }}
  .tile.opened b {{ color: #d97706; }} .tile.resilience b {{ color: #16a34a; }}
  h2 {{ font-size: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; margin: 8px 0 20px; }}
  th {{ background: #f1f5f9; color: #64748b; font-size: 11px; text-align: left; padding: 8px 10px; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #f1f5f9; }}
  .meta {{ color: #475569; font-size: 13px; line-height: 1.7; }}
  .note {{ background: #ecfdf5; color: #065f46; padding: 10px 14px; border-radius: 6px; }}
  .foot {{ color: #64748b; font-size: 12px; margin-top: 24px; line-height: 1.6; }}
</style>
</head>
<body>
<header>
  <h1>SEA-SIM AWARENESS REPORT - {e(st.name)}</h1>
  <p>{e(org)} &middot; {e(st.campaign_id)} &middot; status: {e(st.status)}</p>
</header>
<main>
  <div class="tiles">
    <div class="tile"><b>{st.sent}</b><span>SENT</span></div>
    <div class="tile opened"><b>{st.opened}</b><span>OPENED</span></div>
    <div class="tile clicked"><b>{st.clicked} ({st.click_rate:.1f}%)</b><span>CLICKED</span></div>
    <div class="tile reported"><b>{st.reported} ({st.report_rate:.1f}%)</b><span>REPORTED</span></div>
    <div class="tile"><b>{st.dismissed}</b><span>DISMISSED</span></div>
    <div class="tile resilience"><b>{st.resilience:.1f}%</b><span>RESILIENCE</span></div>
    <div class="tile"><b>{st.trained}</b><span>TRAINED JIT</span></div>
  </div>

  <h2>Campaign</h2>
  <p class="meta">
    Template: {e(st.template_name)} (difficulty {e(st.template_difficulty)})<br>
    Techniques: {e(tech)}<br>
    Run: {e(camp.created)} &rarr; {e(camp.completed_at or '(in progress)')}
  </p>
  {ai_note}

  <h2>Outcomes by department</h2>
  <table>
    <thead><tr><th>Department</th><th>Sent</th><th>Opened</th>
    <th>Clicked</th><th>Reported</th><th>Dismissed</th><th>Click %</th></tr></thead>
    <tbody>{dept_rows or '<tr><td colspan="7">No data.</td></tr>'}</tbody>
  </table>

  <h2>Notes</h2>
  <div class="foot">
    Simulated exercise; no credentials or personal data collected.<br>
    Individual outcomes are for training purposes only, never for discipline.
  </div>
</main>
</body>
</html>"""

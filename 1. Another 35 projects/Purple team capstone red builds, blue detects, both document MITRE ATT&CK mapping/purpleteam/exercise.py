"""Exercise engine: runs the red build, the blue detection pass, computes the
MITRE coverage picture and persists everything so the report can be rebuilt
or re-exported offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import mitre
from .blueteam import run_detections
from .config import LAB_TARGET_DIR, SESSION_FILE, ensure_dirs
from .redteam import reset_lab, run_techniques
from .util import now_iso, pct, stamp, write_json


@dataclass
class Session:
    created: str = ""
    techniques_executed: list[str] = field(default_factory=list)
    techniques_available: list[str] = field(default_factory=lambda: mitre.technique_ids())
    artifacts: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    score: dict = field(default_factory=dict)
    lab_root: str = ""
    run_id: str = ""

    def as_dict(self) -> dict:
        return {
            "created": self.created,
            "run_id": self.run_id,
            "techniques_executed": self.techniques_executed,
            "techniques_available": self.techniques_available,
            "artifacts": self.artifacts,
            "findings": self.findings,
            "timeline": self.timeline,
            "score": self.score,
            "lab_root": self.lab_root,
        }


def new_exercise(lab_root: Path | None = None, reset: bool = True) -> Session:
    lt = Path(lab_root) if lab_root else Path(LAB_TARGET_DIR)
    ensure_dirs()
    if reset:
        reset_lab(lt)
    s = Session(created=now_iso(), run_id="ex_" + stamp(), lab_root=str(lt))
    s.timeline.append({"ts": s.created, "role": "setup", "event": "Lab reset to clean baseline",
                       "technique_id": "", "detail": str(lt)})
    return s


def red_build(s: Session, technique_ids: list[str]) -> Session:
    keep = [t for t in technique_ids if t in mitre.technique_ids()]
    if not keep:
        return s
    # Skip techniques whose module already ran this exercise, so repeated
    # Build clicks only add *new* techniques instead of duplicating artifacts.
    from .redteam import module_for_technique
    already = set()
    for a in s.artifacts:
        m = module_for_technique(str(a.get("technique_id", "")))
        if m:
            already.add(m)
    needed = [t for t in keep if module_for_technique(t) not in already]
    if not needed:
        return s
    artifacts, executed = run_techniques(Path(s.lab_root), s.run_id, needed)
    s.techniques_executed = sorted(set(s.techniques_executed) | set(executed))
    s.artifacts.extend(artifacts)
    for t in artifacts:
        s.timeline.append({
            "ts": t.get("ts"), "role": "red",
            "event": f"[{t['technique_id']}] {t['technique_name']} - {t['event']}",
            "technique_id": t["technique_id"], "detail": t["file"],
        })
    write_index(Path(s.lab_root), s.artifacts)
    s.timeline.append({"ts": now_iso(), "role": "red",
                       "event": f"Red build complete: {len(executed)} technique(s) on target",
                       "technique_id": "", "detail": ", ".join(executed)})
    return s


def blue_detect(s: Session) -> Session:
    findings = run_detections(Path(s.lab_root), s.run_id)
    s.findings = findings
    for f in findings:
        s.timeline.append({
            "ts": f.get("ts"), "role": "blue",
            "event": f"[{f['rule_id']}] {f['rule_name']} -> {f['technique_id']} "
                     f"({f['severity']}/{f['fidelity']})",
            "technique_id": f.get("technique_id", ""), "detail": f.get("file", ""),
        })
    s.timeline.append({"ts": now_iso(), "role": "blue",
                       "event": f"Blue detect pass complete: {len(findings)} finding(s)",
                       "technique_id": "", "detail": ""})
    s.score = score_exercise(s)
    return s


def score_exercise(s: Session) -> dict:
    executed = list(s.techniques_executed)
    findings = s.findings
    tids = set(executed)

    detected_by: dict[str, list[str]] = {t: [] for t in tids}
    fidelity_by: dict[str, str] = {}
    for t in tids:
        firing = sorted({f["rule_id"] for f in findings if f.get("technique_id") == t})
        detected_by[t] = firing
        if any(f.get("fidelity") == "high" for f in findings if f.get("technique_id") == t):
            fidelity_by[t] = "high"
        elif firing:
            fidelity_by[t] = "low"
        else:
            fidelity_by[t] = "none"

    detected = [t for t in tids if detected_by[t]]
    high_fid = [t for t in tids if fidelity_by[t] == "high"]

    matrix = mitre.coverage_matrix(executed, findings)
    rule_hits: dict[str, int] = {}
    for f in findings:
        rule_hits[f["rule_id"]] = rule_hits.get(f["rule_id"], 0) + 1

    gaps = [t for t in tids if not detected_by[t]]
    hi_fidelity_gaps = [t for t in tids if fidelity_by[t] != "high"]

    return {
        "techniques_available": len(mitre.technique_ids()),
        "techniques_executed": len(tids),
        "techniques_detected": len(detected),
        "techniques_high_fidelity": len(high_fid),
        "detection_rate": pct(len(detected), len(tids)),
        "high_fidelity_coverage": pct(len(high_fid), len(tids)),
        "findings_count": len(findings),
        "artifacts_count": len(s.artifacts),
        "red_coverage": pct(len(tids), len(mitre.technique_ids())),
        "detected_by": detected_by,
        "fidelity_by": fidelity_by,
        "rule_hits": rule_hits,
        "gaps": gaps,
        "high_fidelity_gaps": hi_fidelity_gaps,
        "matrix": matrix,
        "rules_fired": sorted(rule_hits.keys()),
    }


def write_index(lab_root: Path, artifacts: list[dict]) -> None:
    write_json(lab_root / ".purpleteam_index.json", artifacts)
    write_json(lab_root / ".purpleteam_run.json",
               {"run_id": artifacts[0]["run_id"] if artifacts else "", "count": len(artifacts)})


def save_session(s: Session) -> Path:
    ensure_dirs()
    write_json(SESSION_FILE, s.as_dict())
    stamped = SESSION_FILE.parent / f"session_{s.run_id}.json"
    write_json(stamped, s.as_dict())
    return stamped


def full_exercise(technique_ids: list[str] | None = None,
                  lab_root: Path | None = None, reset: bool = True, save: bool = True) -> Session:
    """Headless one-shot: build + detect + score (+save). Used by CLI/tests."""
    if technique_ids is None:
        technique_ids = mitre.technique_ids()
    s = new_exercise(lab_root, reset=reset)
    s = red_build(s, technique_ids)
    s = blue_detect(s)
    if save:
        save_session(s)
    return s


def load_last_session() -> Session | None:
    from .util import load_json
    d = load_json(SESSION_FILE, None)
    if not d:
        return None
    s = Session()
    for k, v in d.items():
        if hasattr(s, k):
            setattr(s, k, v)
    return s
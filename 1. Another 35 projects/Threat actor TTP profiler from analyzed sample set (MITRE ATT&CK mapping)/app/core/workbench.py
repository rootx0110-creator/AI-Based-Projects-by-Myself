"""High-level orchestration of sample analysis, ATT&CK mapping and profiler."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .actors import ActorDb
from .attackdb import AttackDb
from .model import AnalysisResult, SampleResult, TechniqueHit
from .pe_analyzer import analyze_file
from .yara_engine import YaraEngine

SUPPORTED_REPORT_SCHEMA_VERSION = 1


class Workbench:
    """In-memory context for the active analysis session."""

    def __init__(self) -> None:
        self.attack_db = AttackDb()
        self.actor_db = ActorDb()
        self.yara = YaraEngine()
        self.reset()

    # ------------------------------------------------------------------
    @property
    def techniques(self) -> Dict[str, TechniqueHit]:
        return self._analysis.techniques

    @property
    def samples(self) -> List[SampleResult]:
        return self._analysis.samples

    @property
    def actors(self):
        return self._analysis.actors

    def reset(self) -> None:
        self._analysis = AnalysisResult()

    def has_data(self) -> bool:
        return len(self._analysis.samples) > 0 and bool(self._analysis.techniques)

    def load_demo(self) -> str:
        """Populate the workbench with synthetic analyzed samples (demonstration
        dataset) and run the full analysis pipeline."""
        import tempfile

        demo = [
            ("demo_agent_a.txt", "plain", [
                "http://evil.example/panel.php",
                "powershell -enc SQBFAFgA",
                "sekurlsa::logonpasswords",
                "schtasks /create",
                "vssadmin delete shadows",
            ]),
            ("demo_agent_b.txt", "plain", [
                "https://gist.github.com/exfil",
                "WanaCrypt0r",
                "bitcoin",
                "139.59.1.1:443",
                "CreateRemoteThread",
            ]),
        ]
        tmp = tempfile.gettempdir()
        samples = []
        for name, ftype, lines in demo:
            path = os.path.join(tmp, "ttp_demo_" + name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            samples.append(SampleResult(
                filepath=path,
                filename=name,
                size_bytes=os.path.getsize(path),
                file_type=ftype,
                strings=list(lines),
                md5="demo-md5-" + name.split(".")[0],
                sha1="demo-sha1-" + name.split(".")[0],
                sha256="demo-sha256-" + name.split(".")[0],
                imports={"kernel32.dll": ["CreateRemoteThread", "VirtualAllocEx"],
                         "advapi32.dll": ["OpenProcessToken", "RegSetValueEx"]},
                dlls=["kernel32.dll", "advapi32.dll", "wininet.dll"],
            ))
        self._analysis.samples = samples
        self.reanalyze()
        return "Demo dataset loaded: %d samples, %d techniques, %d actors." % (
            len(samples), len(self._analysis.techniques), len(self._analysis.actors))

    # ------------------------------------------------------------------
    def add_file(self, path: str) -> SampleResult:
        sample = analyze_file(path)
        self._analysis.samples.append(_decorate_sample(sample))
        return sample

    def add_files(self, paths) -> List[SampleResult]:
        return [self.add_file(p) for p in paths]

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self._analysis.samples):
            self._analysis.samples.pop(index)
        self.reanalyze()

    # ------------------------------------------------------------------
    def load_report(self, path: str) -> SampleResult:
        """Ingest a previously exported JSON report (from this tool or an
        analysis pipeline) as a sample.  Accepts both the native schema and
        a wide variety of common report shapes (dict with imports/strings/
        hashes/yara/behavior keys)."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        sample = _sample_from_report(path, data)
        self._analysis.samples.append(sample)
        return sample

    # ------------------------------------------------------------------
    def reanalyze(self) -> None:
        """Re-run the full detection pipeline over all samples."""
        hits: Dict[str, TechniqueHit] = {}
        for sample in self._analysis.samples:
            self._apply_yara(sample)
            for hit in self.attack_db.match(sample):
                self._merge_hit(hits, hit)
        self._analysis.techniques = hits
        self._analysis.actors = self.actor_db.match(hits)
        iocs_seen = set()
        for s in self._analysis.samples:
            for ioc in s.iocs:
                iocs_seen.add((ioc["type"], ioc["name"]))
        self._analysis.iocs_total = len(iocs_seen)

    def _apply_yara(self, sample: SampleResult) -> None:
        try:
            sample.yara_hits = self.yara.match(sample)
        except Exception:
            sample.yara_hits = []

    @staticmethod
    def _merge_hit(hits: Dict[str, TechniqueHit], hit: TechniqueHit) -> None:
        prev = hits.get(hit.technique_id)
        if prev is None:
            hits[hit.technique_id] = hit
            return
        evidence = list(dict.fromkeys(prev.evidence + hit.evidence))
        conf = min(95.0, max(prev.confidence, hit.confidence) + 3)
        new_hit = TechniqueHit(
            technique_id=hit.technique_id,
            name=hit.name,
            tactics=hit.tactics,
            confidence=round(conf, 1),
            weight=max(prev.weight, hit.weight),
            evidence=evidence,
        )
        hits[hit.technique_id] = new_hit

    # ------------------------------------------------------------------
    def to_report(self, path: str) -> str:
        """Serialize the current analysis to a JSON report file."""
        payload = {
            "schema_version": SUPPORTED_REPORT_SCHEMA_VERSION,
            "tool": "Threat Actor TTP Profiler",
            "generated_at": self._analysis.generated_at,
            "samples": [_sample_to_dict(s) for s in self._analysis.samples],
            "techniques": [
                {
                    "id": t.technique_id,
                    "name": t.name,
                    "tactics": t.tactics,
                    "confidence": t.confidence,
                    "evidence": t.evidence,
                }
                for t in sorted(self._analysis.techniques.values(), key=lambda x: x.technique_id)
            ],
            "actors": [
                {
                    "id": a.actor_id,
                    "name": a.name,
                    "score": a.score,
                    "coverage": a.coverage,
                    "matched_techniques": a.matched_techniques,
                }
                for a in self._analysis.actors
            ],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return path


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _decorate_sample(sample: SampleResult) -> SampleResult:
    return sample


def _sample_from_report(path: str, data: dict) -> SampleResult:
    """Convince a JSON report (many possible shapes) into a SampleResult."""
    sample = SampleResult(filepath=path, filename=os.path.basename(path))
    sample.file_type = str(data.get("file_type", "report"))
    sample.md5 = str(data.get("md5", data.get("hash", "")))
    sample.sha1 = str(data.get("sha1", ""))
    sample.sha256 = str(data.get("sha256", data.get("sha256", "")))
    sample.imports = [str(x) for x in data.get("imports", [])]
    sample.imports += [str(x) for x in data.get("api_calls", [])]
    for s in data.get("strings", []):
        sample.strings.append(str(s))
    sample.dlls = [str(x) for x in data.get("dlls", data.get("libraries", []))]
    for r in data.get("yara", data.get("yara_rules", [])):
        if isinstance(r, dict):
            sample.yara_hits.append(str(r.get("rule", r.get("name", ""))))
        else:
            sample.yara_hits.append(str(r))
    for b in data.get("behavior", []):
        sample.notes.append(str(b))
    sample.notes.append("Ingested from JSON report: %s" % path)
    sample.size_bytes = int(data.get("size", data.get("size_bytes", 0)) or 0)
    sample.error = None
    if not sample.strings and not sample.imports and not sample.yara_hits:
        sample.error = "Report contained no analyzable indicators (imports/strings/yara)."
    return sample
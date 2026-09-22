"""Shared data models used throughout the TTP profiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SampleResult:
    """Result of analyzing a single sample file."""

    filepath: str
    filename: str
    size_bytes: int = 0
    file_type: str = "unknown"          # pe32, pe32+, script, archive, data, plain
    md5: str = ""
    sha1: str = ""
    sha256: str = ""
    machine: str = ""
    compile_time: str = ""
    subsystem: str = ""
    linker_version: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)      # flattened function names
    dlls: List[str] = field(default_factory=list)         # imported library list
    exports: List[str] = field(default_factory=list)
    strings: List[str] = field(default_factory=list)
    debug_pdb: str = ""
    has_tls: bool = False
    has_cert: bool = False
    packer: str = ""
    entropy: float = 0.0
    overlay_size: int = 0
    architecture: str = ""
    yara_hits: List[str] = field(default_factory=list)
    iocs: List[Dict[str, str]] = field(default_factory=list)   # {type,name}
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class TechniqueHit:
    """A detected MITRE ATT&CK technique with supporting evidence."""

    technique_id: str          # e.g. T1055
    name: str
    tactics: List[str]
    confidence: float          # 0..100
    weight: float
    evidence: List[str]        # human readable evidence strings
    matched_rules: List[str] = field(default_factory=list)  # neutral rule ids


@dataclass
class ActorMatch:
    """Threat actor similarity result."""

    actor_id: str
    name: str
    aliases: List[str]
    origin: str
    motivation: str
    first_seen: str
    score: float                # 0..1 overall similarity
    coverage: float             # 0..100 fraction of actor TTPs observed
    matched_techniques: List[str]
    description: str
    tools: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Aggregate result over a set of samples."""

    samples: List[SampleResult] = field(default_factory=list)
    techniques: Dict[str, TechniqueHit] = field(default_factory=dict)
    actors: List[ActorMatch] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    iocs_total: int = 0

    def merge_evidence(self) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for t in self.techniques.values():
            out[t.technique_id] = list(t.evidence)
        return out
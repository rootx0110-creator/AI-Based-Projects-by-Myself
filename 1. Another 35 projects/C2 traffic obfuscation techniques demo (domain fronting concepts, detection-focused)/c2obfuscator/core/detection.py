"""Detection-focused analysis engine.

Evaluates synthetic traffic samples for classic C2 indicators:
entropy, structure, beacon regularity and protocol signatures.
"""
from __future__ import annotations

import base64
import hashlib
import math
import re

from .beacon import BeaconSchedule
from .obfuscators import get_techniques

SIGNATURES: list[dict] = [
    {
        "name": "Base64 blob",
        "pattern": r"^[A-Za-z0-9+/]{32,}={0,2}$",
        "detail": "High-density base64 payload with padding.",
    },
    {
        "name": "Meterpreter-style header",
        "pattern": r"^\x00\x00\x00\x00\x01",
        "detail": "Length-prefixed binary framing common to staging sockets.",
    },
    {
        "name": "Cobalt Strike default UA",
        "pattern": r"Windows-Update-Agent|Mozilla/5.0 \(Windows NT 6\.1; WOW64\)",
        "detail": "Default user agent seen in many C2 frameworks.",
    },
    {
        "name": "HTTP C2 path fingerprint",
        "pattern": r"/api/\w{6,15}|\bfirmware\b|\bupdate\b|/data",
        "detail": "Ambiguous REST-looking paths favoured by beacons.",
    },
]


class DetectionResult:
    def __init__(self) -> None:
        self.entropy = 0.0
        self.hex_ratio = 0.0
        self.printable_ratio = 0.0
        self.beacon_cv = 0.0
        self.beacon_std = 0.0
        self.signature_hits: list[str] = []
        self.sections: list[dict] = []
        self.risk_score = 0
        self.risk_level = "LOW"

    def risk_categories(self) -> list[dict]:
        return [s for s in self.sections if s.get("weight", 0) > 0]

    def to_dict(self) -> dict:
        return {
            "entropy": round(self.entropy, 4),
            "hex_ratio": round(self.hex_ratio, 4),
            "printable_ratio": round(self.printable_ratio, 4),
            "beacon_cv": round(self.beacon_cv, 4),
            "beacon_std": round(self.beacon_std, 3),
            "signature_hits": self.signature_hits,
            "sections": self.sections,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
        }


class DetectionEngine:
    """Bundle several weak indicators into an explainable risk score."""

    @staticmethod
    def entropy(data: bytes) -> float:
        if not data:
            return 0.0
        counts = [0] * 256
        for b in data:
            counts[b] += 1
        n = len(data)
        return -sum(
            (c / n) * math.log2(c / n)
            for c in counts
            if c and c != n
        )

    @staticmethod
    def analyze_payload(data: bytes, metadata: str = "") -> DetectionResult:
        result = DetectionResult()
        result.entropy = DetectionEngine.entropy(data)
        if not data:
            return result

        printable = sum(1 for b in data if 32 <= b <= 126)
        hex_chars = sum(
            1
            for b in data
            if (48 <= b <= 57) or (97 <= b <= 102) or (65 <= b <= 70)
        )
        result.printable_ratio = printable / len(data)
        result.hex_ratio = hex_chars / len(data)

        sample = metadata + "\n" + (
            data[:64].decode("latin-1", errors="replace")
        )
        for sig in SIGNATURES:
            if re.search(sig["pattern"], sample, re.IGNORECASE):
                result.signature_hits.append(f"{sig['name']} :: {sig['detail']}")

        sections: list[dict] = []
        e = result.entropy
        sections.append(
            {
                "finding": "payload_entropy",
                "value": round(e, 3),
                "comment": "Binary / encrypted data has high entropy"
                if e > 6.5
                else "Mostly structured / plaintext data",
                "weight": 25 if e > 6.5 else 0,
            }
        )
        no_plain = result.printable_ratio < 0.5
        sections.append(
            {
                "finding": "non_printable",
                "value": round(result.printable_ratio, 3),
                "comment": "Less than half of bytes are printable - unusual for web content",
                "weight": 20 if no_plain else 0,
            }
        )
        sections.append(
            {
                "finding": "signature_matches",
                "value": len(result.signature_hits),
                "comment": "; ".join(result.signature_hits) or "No framework signatures",
                "weight": 15 * min(3, len(result.signature_hits)),
            }
        )
        sections.append(
            {
                "finding": "compact_sessions",
                "value": 1 if len(data) < 1_500 else 0,
                "comment": "Payload unusually small for host-to-host data transfer",
                "weight": 10 if len(data) < 1_500 else 0,
            }
        )

        result.sections = sections
        score = sum(s["weight"] for s in sections)
        if score >= 50:
            level = "HIGH"
        elif score >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"
        result.risk_score = min(100, score)
        result.risk_level = level
        return result

    @staticmethod
    def analyze_beacon(
        interval: float, jitter_pct: float, count: int, seed: int
    ) -> tuple[dict, list[float]]:
        sched = BeaconSchedule(
            interval=interval, jitter_pct=jitter_pct, count=count, seed=seed
        )
        stats = sched.stats()
        result = DetectionResult()
        result.beacon_cv = stats["coefficient_of_variation"]
        result.beacon_std = stats["interval_std"]
        cv = result.beacon_cv
        if cv < 0.05:
            tag = "REGULAR"
            weight = 30
        elif cv < 0.25:
            tag = "JITTERED"
            weight = 18
        elif cv < 0.6:
            tag = "IRREGULAR"
            weight = 7
        else:
            tag = "NOISY"
            weight = 0
        result.sections = [
            {
                "finding": f"beacon_{tag.lower()}",
                "value": round(cv, 4),
                "comment": f"CoV={cv:.3f} - fixed-interval check-in rhythm",
                "weight": weight,
            }
        ]
        result.risk_score = weight
        result.risk_level = (
            "HIGH" if weight >= 25 else "MEDIUM" if weight >= 15 else "LOW"
        )
        return result, sched.generate()

    @staticmethod
    def build_sample_variants(seed: int = 7) -> list[dict]:
        """Bytes payload plus metadata used for the detection lab."""
        cmd = b"GET /status?host=WS-0001&user=jsmith&ver=1.0.4 HTTP/1.1"
        variants = []
        for tech in get_techniques(seed):
            encoded = tech.encode(cmd)
            variants.append(
                {
                    "technique": tech.name,
                    "category": tech.category,
                    "plain": cmd.decode(),
                    "encoded_hex": encoded.hex()[:96] + (
                        "..." if len(encoded) > 48 else ""
                    ),
                    "encoded_len": len(encoded),
                    "entropy": round(DetectionEngine.entropy(encoded), 3),
                }
            )
        return variants
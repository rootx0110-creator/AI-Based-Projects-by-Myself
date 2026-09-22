"""Domain fronting concept model.

Shows how TLS SNI / HTTPS Host-header mismatches work in theory: the
connection is fronted by a CDN/edge host while the Host header names the
real destination. Detection focuses on the mismatch visibility from
TLS record data vs HTTP headers.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FrontingRequest:
    """A single synthetic HTTPS request description."""

    method: str = "POST"
    path: str = "/api/v3/session"
    host_header: str = "cdn-facade.example-cdn.com"
    tls_sni: str = "internal.defender.example.com"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    payload_bytes: int = 512
    encrypted: bool = True

    def features(self) -> dict:
        return {
            "method": self.method,
            "path": self.path,
            "host_header": self.host_header,
            "tls_sni": self.tls_sni,
            "user_agent": self.user_agent,
            "payload_bytes": self.payload_bytes,
            "encrypted": self.encrypted,
        }


@dataclass
class FrontingAnalysis:
    """Result of contrasting TLS-visible vs HTTP-visible fields."""

    request: FrontingRequest
    sni_visible: str = "Yes - SNI is plaintext in ClientHello"
    host_visible: str = "Yes - after TLS decryption / TLS-inspection"
    match: bool = False
    redirections: list[str] = field(default_factory=list)
    detector_notes: list[str] = field(default_factory=list)
    risk_score: int = 0


class DomainFrontingAnalyzer:
    """Analyse a synthetic fronting request and produce detection notes."""

    @staticmethod
    def analyze(request: FrontingRequest) -> FrontingAnalysis:
        match = request.tls_sni.lower() == request.host_header.lower()
        notes: list[str] = []
        ops_risk = 0
        redirections: list[str] = []

        if not match:
            notes.append(
                "Mismatch: TLS SNI and HTTP Host differ - classic domain fronting."
            )
            ops_risk += 45
            notes.append(
                "Detection: compare TLS SNI vs Host once TLS is terminated."
            )
        else:
            notes.append("SNI == Host: ordinary direct HTTPS connection.")

        if request.encrypted:
            ops_risk += 20
            notes.append(
                "Encrypted payload: DPI cannot inspect body; rely on TLS metadata."
            )
        if "cdn" in request.host_header.lower():
            notes.append(
                "Host is an edge/CDN name - consistent with public fronting service."
            )
            ops_risk += 10
        if request.payload_bytes > 200:
            notes.append("Payload larger than benign page fetch - potential callback.")
            ops_risk += 15
        if "Bot" in request.user_agent or "curl" in request.user_agent:
            notes.append("Non-browser user agent observed.")
            ops_risk += 10

        redirections = (
            [
                f"ClientHello -> SNI: {request.tls_sni} (plaintext, always visible)",
                f"HTTP/1.1 Host: {request.host_header} (visible post-TLS-inspection)",
                f"Route: fronting CDN selects backend by Host header",
            ]
            if not match
            else ["Direct connection, no fronting layer detected."]
        )

        return FrontingAnalysis(
            request=request,
            match=match,
            redirections=redirections,
            detector_notes=notes,
            risk_score=min(100, ops_risk),
        )

    @staticmethod
    def suggested_controls(fronting_detected: bool) -> list[str]:
        base = [
            "Uphold egress allow-listing of domains/IPs, not just ports.",
            "Central TLS-inspection point to surface Host-header vs SNI.",
            "Log SNI + Host + destination IP co-occurrence to one row.",
            "Watch for highly randomised paths under CDN hostnames.",
        ]
        if fronting_detected:
            base.insert(0, "Flag SNI/Host mismatches to a SOC analyst queue.")
        return base
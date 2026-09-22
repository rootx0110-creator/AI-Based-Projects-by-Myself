---
name: domain-fronting-lab
description: Walk through the domain fronting detection exercise for the C2 Traffic Obfuscation Lab. Use when explaining or analysing the TLS SNI vs HTTP Host-header mismatch, its visibility to different inspectors, and suggested defensive controls.
---

# Domain Fronting Lab

Explain and analyse the domain fronting concept from a **detection** point of
view, using only synthetic data.

## When to use
- Explaining how domain fronting works (SNI vs Host mismatch)
- Analysing a fronting request for detection-relevant signals
- Producing the Domain Fronting section of the HTML report

## Key concept to convey
- **TLS SNI** is plaintext in the ClientHello - visible to any network observer.
- **HTTP Host header** is inside the TLS stream - only visible with TLS
  inspection / decryption.
- Fronting = the client connects to a public CDN/edge (SNI) but requests a
  different backend (Host header). Detection is the mismatch plus metadata.

## Workflow

1. Build a request and analyse it:

```python
from c2obfuscator.core import DomainFrontingAnalyzer, FrontingRequest

req = FrontingRequest(
    tls_sni="internal.defender.example.com",
    host_header="cdn-facade.example-cdn.com",
    encrypted=True,
)
a = DomainFrontingAnalyzer.analyze(req)
controls = DomainFrontingAnalyzer.suggested_controls(not a.match)
```

2. Report these fields:
- `a.match` (SNI == Host?)
- `a.risk_score` (0-100)
- `a.redirections` - the connection flow
- `a.detector_notes` - the indicator narrative
- `controls` - defensive suggestions

## Output format
Give a concise walkthrough: connection flow, mismatch status, risk score,
top 3 windows of detection visibility, and 3 controls. If a report is needed,
feed the analysis dict to the `html-report-generator` skill.
---
name: html-report-generator
description: Generate the self-contained styled HTML report for the C2 Traffic Obfuscation Lab. Use when a user wants a session exported to a portable HTML report with inline SVG charts and no external dependencies.
---

# HTML Report Generator

Turn a completed C2 Obfuscation Lab session into a standalone, dark-themed
HTML report (inline CSS + SVG, zero external assets, offline-safe).

## When to use
- User asks to "export", "save the report", or "make an HTML report"
- A beacon/fronting/detection analysis should be persisted for review

## Workflow

1. Ensure the session has data. Minimal viable inputs:
   - `beacon`: `{stats: {...}, verdict: {...}, rows: [...]}`
   - `fronting`: `{detector_notes: [...], controls: [...], risk_score: int,
     match: bool, tls_sni: str, host_header: str}`
   - `detection`: `{sections: [...], signature_hits: [...], risk_score: int,
     risk_level: str}`

2. Generate:

```python
from c2obfuscator.reporting import build_html_report

html = build_html_report(
    name="Session title",
    summary={"badges": []},
    techniques=[{"name": t.name, "category": t.category, "description": t.description}
                for t in get_techniques(7)],
    env_variants=DetectionEngine.build_sample_variants(7),
    beacon_stats=beacon["stats"],
    beacon_verdict=beacon["verdict"],
    beacon_row_data=beacon["rows"],
    fronting=fronting,
    detection=detection,
)
open("c2-obfuscation-report.html", "w", encoding="utf-8").write(html)
```

3. Validate the output:
   - File size > 8 KB for a full session
   - Contains `<svg`, `<style>` and no `http(s)://` external links
   - Opens offline in any browser

## Output notes
- Report sections: session summary, technique catalogue, encoded payload
  versions, beacon schedule + SVG chart, domain fronting SNI/Host view,
  detection findings.
- The GUI exports this automatically from the **HTML Report** tab.
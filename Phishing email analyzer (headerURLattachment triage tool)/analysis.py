import time
from datetime import datetime, timezone

from engine.email_parser import EmlMail
from engine.header_analyzer import HeaderAnalyzer
from engine.url_analyzer import URLAnalyzer
from engine.attachment_analyzer import AttachmentAnalyzer
from engine.risk_scorer import RiskScorer


def run_analysis(email_obj: EmlMail) -> dict:
    """Execute the full triage pipeline and return a result bundle."""
    started = time.perf_counter()

    headers = HeaderAnalyzer(email_obj).analyze()
    urls = URLAnalyzer(email_obj.urls).analyze()
    atts = AttachmentAnalyzer(email_obj.attachments).analyze()

    evidence = headers["evidence"] + urls["evidence"] + atts["evidence"]
    scorer = RiskScorer(evidence)
    summary = scorer.breakdown()

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "headers": headers,
        "urls": urls,
        "attachments": atts,
        "evidence": evidence,
        "summary": summary,
        "raw_headers": email_obj.raw_headers,
        "meta": {
            "source": email_obj.source_name,
            "subject": email_obj.subject,
            "from": email_obj.from_addr,
            "date": email_obj.date,
            "url_count": len(email_obj.urls),
            "att_count": len(email_obj.attachments),
            "elapsed_ms": elapsed_ms,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    }
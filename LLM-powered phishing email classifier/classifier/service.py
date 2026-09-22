"""Scan pipeline service: parse -> extract -> score -> fuse -> store."""

from __future__ import annotations

import datetime
import uuid

from . import fusion, heuristic, llm
from .extractor import extract_features, printable_from
from .parser import parse_email


class ScanStore:
    """In-memory scan store. Email content is held only while the app runs."""

    def __init__(self) -> None:
        self.scans: dict[str, dict] = {}

    def put(self, analysis_id: str, result: dict) -> None:
        self.scans[analysis_id] = result

    def get(self, analysis_id: str) -> dict | None:
        return self.scans.get(analysis_id)

    def recent(self, limit: int = 6) -> list[dict]:
        return [v for _, v in sorted(self.scans.items(), reverse=True)][:limit]


store = ScanStore()


def scan_email(raw: str, subject: str | None = None, sender: str | None = None,
               recipient: str | None = None, use_llm: bool | None = None) -> dict:
    """Run a full scan. Returns the stored ScanResult dict."""

    content = raw or ""
    if sender or recipient or subject:
        header_lines = []
        if sender:
            header_lines.append(f"From: {sender}")
        if subject:
            header_lines.append(f"Subject: {subject}")
        if recipient:
            header_lines.append(f"To: {recipient}")
        content = "\n".join(header_lines) + "\n\n" + content

    email_obj = parse_email(content)
    email_dict = email_obj.to_dict()
    email_dict["sender_readable"] = printable_from(email_obj)

    evidence = [e.to_dict() for e in extract_features(email_obj)]

    score = heuristic.score(evidence)

    llm_result = None
    settings = llm.load_settings()
    use_llm_flag = _resolve_llm_use(use_llm, settings)
    if use_llm_flag:
        llm_result = llm.analyze(email_obj, settings)

    analysis_id = uuid.uuid4().hex[:12]
    scanned_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = fusion.fuse(analysis_id, score, llm_result, email_dict, scanned_at)
    payload = result.to_dict()
    store.put(analysis_id, payload)
    return payload


def _resolve_llm_use(flag: bool | None, settings: dict) -> bool:
    if flag is not None:
        return bool(flag)
    return llm.is_available(settings)


def health() -> dict:
    settings = llm.load_settings()
    return {
        "status": "ok",
        "version": "1.0.0",
        "llm_enabled": llm.is_available(settings),
        "llm_model": settings.get("model") if llm.is_available(settings) else None,
        "scans_held": len(store.scans),
    }
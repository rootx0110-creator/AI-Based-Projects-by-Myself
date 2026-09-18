"""Event log ingestion via the Windows 'wevtutil' command line utility.

Supports live channels and .evtx files. Produces EventRecord objects
with structured <Data Name=...> fields.
"""
from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Tuple

from .models import EventRecord

_EV_NS = "http://schemas.microsoft.com/win/2004/08/events/event"

LIVE_CHANNELS: List[str] = [
    "Security",
    "System",
    "Application",
    "Microsoft-Windows-PowerShell/Operational",
    "Microsoft-Windows-Sysmon/Operational",
    "Microsoft-Windows-TaskScheduler/Operational",
    "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
    "Microsoft-Windows-Shell-Core/Operational",
    "Windows PowerShell",
]

TIME_CHOICES = [
    ("Last hour", 3600),
    ("Last 24 hours", 86400),
    ("Last 7 days", 604800),
    ("Last 30 days", 2592000),
    ("Everything", None),
]


class ParseCanceled(Exception):
    pass


def _strip(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _parse_iso(text: str) -> Optional[datetime]:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_event(raw: str) -> Optional[EventRecord]:
    if not raw.strip():
        return None
    try:
        e = ET.fromstring(raw)
    except ET.ParseError:
        return None

    rec = EventRecord(
        record_id=0, event_id=0, timestamp=datetime.now(timezone.utc),
        channel="", computer="", provider="", level=0, raw=raw,
    )
    for child in e:
        tag = _strip(child.tag)
        if tag == "System":
            for f in child:
                name = _strip(f.tag)
                if name == "EventID":
                    try:
                        rec.event_id = int((f.text or "0").strip())
                    except ValueError:
                        rec.event_id = 0
                elif name == "TimeCreated":
                    rec.timestamp = _parse_iso(f.attrib.get("SystemTime", "")) or rec.timestamp
                elif name == "Channel":
                    rec.channel = (f.text or "").strip()
                elif name == "Computer":
                    rec.computer = (f.text or "").strip()
                elif name == "Provider":
                    rec.provider = f.attrib.get("Name", "") or (f.text or "").strip()
                elif name == "EventRecordID":
                    try:
                        rec.record_id = int((f.text or "0").strip())
                    except ValueError:
                        pass
                elif name == "Level":
                    try:
                        rec.level = int((f.text or "0").strip())
                    except ValueError:
                        pass
        elif tag == "EventData":
            idx = 0
            for f in child:
                name = _strip(f.tag)
                if name == "Data":
                    key = (f.attrib.get("Name") or "").strip() or f"Data{idx}"
                    val = (f.text or "").strip()
                    rec.data[key] = val
                    idx += 1
                elif name == "Binary":
                    rec.data.setdefault("Binary", (f.text or "").strip())
    return rec


def _wrap_parse_fragment(frag: str) -> Optional[EventRecord]:
    return _parse_event(frag)


def _iter_events_from_xml(text: str, callback: Callable, counter: Optional[Callable] = None):
    """Yield EventRecords from wevtutil XML output.

    Splits on '' boundaries because wevtutil emits a sequence of
    standalone <Event ...> elements.
    """
    text = text.replace("\ufeff", "").strip()
    if not text.startswith("<"):
        cut = text.find("<")
        if cut < 0:
            return
        text = text[cut:]
    # If the output is wrapped in a root document (rare), handle gracefully.
    if text.startswith("<?xml"):
        text = text.split("?>", 1)[-1]
    text = text.strip()
    if text.lower().startswith("<root>"):
        raw_events = re.findall(r"<Event\b.*?</Event>", text, flags=re.S)
    else:
        raw_events = re.findall(r"<Event\b.*?</Event>", text, flags=re.S)
    total = len(raw_events)
    if counter is not None:
        counter(total)
    for idx, frag in enumerate(raw_events):
        rec = _wrap_parse_fragment(frag)
        if rec is not None:
            yield rec
        if callback is not None and idx % 50 == 0:
            callback(idx + 1, total)


def _time_query(start: Optional[datetime], end: Optional[datetime]) -> Optional[str]:
    if not start and not end:
        return None

    def fmt(dt: datetime) -> str:
        # naive datetimes are treated as local wall-clock (as produced
        # by datetime.now()); astimezone converts them correctly to UTC.
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    bits = ["*[System["]
    if start:
        bits.append(f"TimeCreated[@SystemTime>='{fmt(start)}']")
    if start and end:
        bits.append(" and ")
    if end:
        bits.append(f"TimeCreated[@SystemTime<='{fmt(end)}']")
    bits.append("]]")
    return "".join(bits)


def events_from_wevtutil(
    target: str,
    max_events: int = 100000,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[List[EventRecord], Optional[str]]:
    """Query wevtutil and parse results into EventRecord list.

    Returns (records, error_message). error is None on success.
    """
    q = _time_query(start, end)
    cmd = ["wevtutil", "qe", target, "/f:xml", "/rd:true", f"/c:{int(max_events)}"]
    if q:
        cmd.append(f"/q:{q}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return [], "wevtutil not found on this system."
    except OSError as exc:
        return [], f"Failed to start wevtutil: {exc}"

    out, err = proc.communicate(timeout=900)

    if cancel_check is not None and cancel_check():
        raise ParseCanceled("Analysis canceled by user.")
    if proc.returncode != 0:
        msg = (err.decode("utf-8", "replace") or "").strip().splitlines()
        return [], "; ".join(msg[-3:]) or f"wevtutil exited with code {proc.returncode}"

    text = out.decode("utf-8", "replace")

    events: List[EventRecord] = []
    for rec in _iter_events_from_xml(text, progress):
        events.append(rec)
    return events, None


def get_wevtutil_version() -> Optional[str]:
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            ["wevtutil", "eum"], capture_output=True, text=True, timeout=30,
            creationflags=flags,
        )
        return (proc.stdout or proc.stderr or "wevtutil").splitlines()[0].strip()
    except Exception:
        return None
"""Email parsing utilities.

Splits raw input into header fields (From/To/Subject/Date) and body.
Tolerant of both loosely formatted raw text and RFC-ish (EML) content.
"""

from __future__ import annotations

import re
from email import policy
from email.parser import Parser as EmailParser
from email.utils import parseaddr

_HEADER_NAMES = ("from", "to", "subject", "date", "reply-to", "cc", "return-path")


def _bx(display_name: str, address: str) -> tuple[str, str]:
    """Repeat parseaddr on a possibly pre-parsed piece for safety."""
    return display_name, address


def clean_field(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[\r\n\t]+", " ", str(value)).strip()


def extract_sender(value: str | None) -> tuple[str, str]:
    """Return (display_name, email_address) from a From/Reply-To value."""
    if not value:
        return "", ""
    display, addr = parseaddr(value)
    if not addr and "@" in value:
        candidates = re.findall(r"[\w.+-]+@[\w.-]+", value)
        if candidates:
            addr = candidates[-1]
            label = re.sub(r"[\w.+-]+@[\w.-]+", "", value).strip(" <>\t")
            display = label or display
    return _bx(display.strip(), addr.strip().lower())


def domain_of(email_address: str) -> str:
    email_address = (email_address or "").lower()
    if "@" not in email_address:
        return ""
    return email_address.rsplit("@", 1)[1].strip()


class ParsedEmail:
    def __init__(self) -> None:
        self.from_display: str = ""
        self.from_email: str = ""
        self.from_domain: str = ""
        self.reply_to_email: str = ""
        self.reply_to_domain: str = ""
        self.to: str = ""
        self.subject: str = ""
        self.date: str = ""
        self.headers: dict[str, str] = {}
        self.body: str = ""

    def to_dict(self) -> dict:
        return {
            "from_display": self.from_display,
            "from_email": self.from_email,
            "from_domain": self.from_domain,
            "reply_to_email": self.reply_to_email,
            "reply_to_domain": self.reply_to_domain,
            "to": self.to,
            "subject": self.subject,
            "date": self.date,
            "body": self.body,
        }


def _simple_split(raw: str) -> tuple[str, str]:
    """Split header block from body using first blank line."""
    match = re.split(r"\r?\n\r?\n", raw, maxsplit=1)
    if len(match) == 2:
        return match[0], match[1]
    return raw, ""


def parse_email(raw: str) -> ParsedEmail:
    raw = (raw or "").replace("\r\n", "\n")
    header_block, body = _simple_split(raw)

    parsed = ParsedEmail()
    headers: dict[str, str] = {}

    if re.match(r"^(from|to|subject|date):", header_block, re.I | re.M):
        # RFC-ish: real header block, use email.parser
        try:
            msg = EmailParser(policy=policy.default).parsestr(raw)
            for name in _HEADER_NAMES:
                headers[name] = clean_field(msg.get(name, ""))
            body = msg.get_body(preferencelist=("plain",))
            if body is not None:
                try:
                    body = body.get_content()
                except Exception:
                    body = msg.get_payload() or ""
            else:
                payload = msg.get_payload()
                body = payload if isinstance(payload, str) else (payload or [""])[0] if payload else ""
        except Exception:
            headers = {}
    else:
        # free-form line scan
        for line in header_block.split("\n"):
            m = re.match(r"^\s*(from|to|subject|date|reply-to|cc)\s*:\s*(.*)$", line, re.I)
            if m:
                headers[m.group(1).lower()] = m.group(2).strip()

    parsed.headers = headers
    parsed.from_display, parsed.from_email = extract_sender(headers.get("from", ""))
    parsed.from_domain = domain_of(parsed.from_email)
    _rt_email, _ = extract_sender(headers.get("reply-to", ""))
    parsed.reply_to_email = _rt_email
    parsed.reply_to_domain = domain_of(_rt_email)
    parsed.to = headers.get("to", "")
    parsed.subject = headers.get("subject", "")
    parsed.date = headers.get("date", "")
    parsed.body = (body or "").strip()

    if not parsed.from_email and not parsed.subject:
        # No headers at all -> treat whole input as message body with
        # a best-effort "From:" sniff inside the text.
        sniff = re.search(r"(?im)^\s*(from|sender)\s*:?\s*([^\n]+)", raw)
        if sniff:
            parsed.from_display, parsed.from_email = extract_sender(sniff.group(2))
            parsed.from_domain = domain_of(parsed.from_email)
    return parsed
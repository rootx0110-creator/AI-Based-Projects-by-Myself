import email
import email.policy
from email import message_from_bytes
import os
import re
from email.header import decode_header


class EmlMail:
    """Parsed email wrapper exposing normalized headers, body parts, urls, attachments."""

    def __init__(self, raw_source: str, source_name: str = "pasted-source"):
        self.source_name = source_name
        policy = email.policy.default
        self.msg = message_from_bytes(raw_source.encode("utf-8", "surrogateescape"), policy=policy)

        self.all_headers = {}
        self.raw_headers = ""
        self.subject = ""
        self.from_addr = ""
        self.to_addr = ""
        self.cc_addr = ""
        self.reply_to = ""
        self.date = ""
        self.message_id = ""
        self.spf = ""
        self.dkim = ""
        self.dmarc = ""

        self.body_text = ""
        self.body_html = ""
        self.urls = []
        self.attachments = []
        self.parse()

    # ------------------------------------------------------------------ #
    #  Public parse
    # ------------------------------------------------------------------ #
    def parse(self):
        self._collect_headers()
        self._extract_known_fields()
        self._walk_parts()

    # ------------------------------------------------------------------ #
    #  Header collection
    # ------------------------------------------------------------------ #
    def _collect_headers(self):
        items = []
        self.raw_headers = self._raw_header_block()
        for k, v in self.msg.items():
            items.append((str(k), self._decode_value(v)))
        for name, value in items:
            if name.lower() in self.all_headers:
                self.all_headers[name.lower()].append(value)
            else:
                self.all_headers[name.lower()] = [value]

    def _raw_header_block(self) -> str:
        lines = []
        for line in str(self.msg).splitlines():
            if line.strip():
                lines.append(line)
            else:
                break
        return "\n".join(lines)

    def _decode_value(self, value) -> str:
        try:
            parts = decode_header(str(value))
            out = []
            for chunk, enc in parts:
                if isinstance(chunk, bytes):
                    out.append(chunk.decode(enc or "utf-8", "replace"))
                else:
                    out.append(str(chunk))
            return "".join(out)
        except Exception:
            return str(value)

    def _extract_known_fields(self):
        g = lambda n: self._get_first(n)
        self.subject = g("subject") or "(no subject)"
        self.from_addr = g("from") or ""
        self.to_addr = g("to") or ""
        self.cc_addr = g("cc") or ""
        self.reply_to = g("reply-to") or ""
        self.date = g("date") or ""
        self.message_id = g("message-id") or ""
        self.spf = self._extract_auth("spf")
        self.dkim = self._extract_auth("dkim")
        self.dmarc = self._extract_auth("dmarc")
        self.return_path = g("return-path") or ""

    def _get_first(self, name) -> str:
        values = self.all_headers.get(name.lower())
        if not values:
            return ""
        return values[0].strip()

    def _extract_auth(self, kind: str) -> str:
        for hdr in ("authentication-results", "received-spf"):
            values = self.all_headers.get(hdr)
            if not values:
                continue
            for val in values:
                formatted = val.lower()
                if kind in formatted:
                    return val
        return ""

    # ------------------------------------------------------------------ #
    #  Body parts / urls / attachments
    # ------------------------------------------------------------------ #
    def _walk_parts(self):
        self._walk(self.msg)
        # Deduplicate urls preserving order
        seen = set()
        uniq = []
        for u in self.urls:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        self.urls = uniq

    def _walk(self, part):
        if part.is_multipart():
            for sub in part.iter_parts():
                self._walk(sub)
        else:
            ctype = (part.get_content_type() or "").lower()
            cdisp = (part.get_content_disposition() or "").lower()
            if cdisp == "attachment":
                self._collect_attachment(part)
                return
            if ctype == "text/plain":
                self._collect_text(part, html=False)
            elif ctype == "text/html":
                self._collect_text(part, html=True)
            else:
                # unknown inline content type — could still be a link carrier
                self._collect_text(part, html=True)

    def _collect_text(self, part, html: bool):
        try:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, "replace")
        except Exception:
            try:
                text = str(part.get_payload())
            except Exception:
                return
        if html:
            self.body_html += text + "\n"
        else:
            self.body_text += text + "\n"
        # Extract URLs from text or html
        self.urls.extend(self._extract_urls(text))

    def _collect_attachment(self, part):
        filename = part.get_filename() or "attachment.bin"
        payload = part.get_payload(decode=True)
        ctype = part.get_content_type() or "application/octet-stream"
        self.attachments.append({
            "filename": filename,
            "content_type": ctype,
            "size": len(payload) if payload else 0,
            "payload": payload or b"",
        })

    # ------------------------------------------------------------------ #
    #  URL extraction
    # ------------------------------------------------------------------ #
    _URL_RE = re.compile(
        r"(?i)\b((?:https?|ftp)://[^\s<>\"']+|www\.[^\s<>\"']+)"
    )

    def _extract_urls(self, text: str):
        found = []
        for m in self._URL_RE.findall(text):
            url = m.strip().rstrip(".,;:!?)")
            if url:
                found.append(url)
        return found

    @property
    def has_attachments(self) -> bool:
        return bool(self.attachments)

    @property
    def message_size(self) -> int:
        try:
            return len(self.msg.as_bytes())
        except Exception:
            return len(str(self.msg))
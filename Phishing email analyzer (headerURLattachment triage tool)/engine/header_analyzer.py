import re
from email.utils import parseaddr, getaddresses


class HeaderAnalyzer:
    """Forensic examination of email headers for spoofing / phishing indicators."""

    def __init__(self, email_obj):
        self.email = email_obj
        self.evidence = []
        self.findings = []

    # ------------------------------------------------------------------ #
    def analyze(self) -> dict:
        self._check_sender_spoofing()
        self._check_reply_to()
        self._check_auth_results()
        self._check_headers_presence()
        self._check_ip_literals_in_headers()
        return {
            "evidence": self.evidence,
            "findings": self.findings,
            "metadata": {
                "from": self.email.from_addr,
                "to": self.email.to_addr,
                "cc": self.email.cc_addr,
                "subject": self.email.subject,
                "reply_to": self.email.reply_to,
                "date": self.email.date,
                "message_id": self.email.message_id,
                "spf": self.email.spf,
                "dkim": self.email.dkim,
                "dmarc": self.email.dmarc,
            },
        }

    # ------------------------------------------------------------------ #
    def _add_finding(self, severity: str, title: str, detail: str, weight: int):
        self.findings.append({
            "severity": severity,
            "title": title,
            "detail": detail,
        })
        if weight > 0:
            self.evidence.append({"source": "headers", "label": title, "detail": detail, "weight": weight})

    # ------------------------------------------------------------------ #
    def _check_sender_spoofing(self):
        raw_from = self.email.from_addr
        if not raw_from:
            self._add_finding("high", "Missing From header", "Email has no sender.", 15)
            return
        display, addr = parseaddr(raw_from)
        if not addr:
            self._add_finding("high", "Invalid From address", f"'{raw_from}' could not be parsed.", 15)
            return
        friendly = display.lower().replace(" ", "").replace("_", "").replace(".", "")
        local = addr.split("@")[0].lower().replace(".", "") if "@" in addr else addr.lower()
        if friendly and local and friendly not in local and local not in friendly:
            # display name contains a brand that differs from the actual address
            brands = self._known_brands(friendly)
            if brands:
                self._add_finding(
                    "critical", "Sender name/address mismatch",
                    f"Display name '{display}' contains brand(s) {brands} but address is '{addr}'.",
                    40,
                )
        # domain side: brand inside domain but wrong registrar
        dom = addr.split("@")[-1].lower() if "@" in addr else ""
        brand = self._brand_in_domain(dom)
        if brand and not self._is_official_domain(brand, dom):
            self._add_finding(
                "high", "Spoofed brand domain",
                f"Sender domain '{dom}' impersonates brand '{brand}' but is not an "
                f"official domain.",
                30,
            )

    @staticmethod
    def _brand_in_domain(domain: str) -> str | None:
        brands = {
            "paypal": "paypal.com",
            "amazon": "amazon.com",
            "apple": "apple.com",
            "microsoft": "microsoft.com",
            "google": "google.com",
            "netflix": "netflix.com",
            "facebook": "facebook.com",
            "bank of america": "bankofamerica.com",
            "wells fargo": "wellsfargo.com",
            "chase": "chase.com",
            "ebay": "ebay.com",
            "linkedin": "linkedin.com",
            "dropbox": "dropbox.com",
            "github": "github.com",
            "outlook": "outlook.com",
            "windows": "microsoft.com",
            "icloud": "icloud.com",
            "office365": "microsoft.com",
            "stripe": "stripe.com",
            "coinbase": "coinbase.com",
        }
        normalized = domain.lower().replace("_", "").replace("-", "")
        for brand, official in brands.items():
            b = brand.replace(" ", "")
            if b in normalized:
                return brand
        return None

    @staticmethod
    def _is_official_domain(brand: str, domain: str) -> bool:
        official_map = {
            "paypal": ("paypal.com", "paypal.co.uk"),
            "amazon": ("amazon.com",),
            "apple": ("apple.com",),
            "microsoft": ("microsoft.com", "windows.com", "outlook.com"),
            "google": ("google.com", "gmail.com", "youtube.com"),
            "netflix": ("netflix.com",),
            "facebook": ("facebook.com",),
            "bank of america": ("bankofamerica.com",),
            "wells fargo": ("wellsfargo.com",),
            "chase": ("chase.com",),
            "ebay": ("ebay.com",),
            "linkedin": ("linkedin.com",),
            "dropbox": ("dropbox.com",),
            "github": ("github.com",),
            "outlook": ("outlook.com",),
            "windows": ("microsoft.com", "windows.com", "outlook.com"),
            "icloud": ("icloud.com",),
            "office365": ("microsoft.com", "outlook.com"),
            "stripe": ("stripe.com",),
            "coinbase": ("coinbase.com",),
        }
        dom = domain.lower()
        return any(dom == off or dom.endswith("." + off) for off in official_map.get(brand, ()))

    @staticmethod
    def _known_brands(text: str) -> list:
        brands = [
            "paypal", "amazon", "apple", "google", "microsoft", "netflix",
            "facebook", "bankofamerica", "wellsfargo", "chase", "ebay",
            "linkedin", "dropbox", "github", "outlook", "windows", "icloud",
            "office", "payoneer", "stripe", "coinbase",
        ]
        found = []
        lowered = text.lower()
        for b in brands:
            if b in lowered:
                found.append(b)
        return found

    def _check_reply_to(self):
        from_addr = parseaddr(self.email.from_addr)[1]
        reply_to = parseaddr(self.email.reply_to)[1]
        if from_addr and reply_to and from_addr.lower() != reply_to.lower():
            self._add_finding(
                "medium", "Reply-To mismatch",
                f"From is '{from_addr}' but Reply-To is '{reply_to}'. "
                f"Replies may go to an attacker-controlled address.",
                10,
            )
        elif not from_addr and reply_to:
            self._add_finding("medium", "Reply-To without From",
                              "Reply-To exists but no From was found.", 5)

    def _check_auth_results(self):
        if self.email.spf:
            if any(w in self.email.spf.lower() for w in ("fail", "softfail", "polrec", "neutral")):
                self._add_finding("high", "SPF failure",
                                  f"SPF did not authenticate: {self.email.spf.strip()}", 15)
        else:
            self._add_finding("low", "No SPF result",
                              "No SPF authentication result found for this email.", 5)
        if not self.email.dkim:
            self._add_finding("low", "No DKIM result",
                              "No DKIM signature/result found.", 3)
        if self.email.dmarc and "fail" in self.email.dmarc.lower():
            self._add_finding("high", "DMARC failure",
                              f"DMARC policy did not pass: {self.email.dmarc.strip()}", 15)
        elif not self.email.dmarc:
            self._add_finding("low", "No DMARC result",
                              "No DMARC result found.", 3)

    def _check_headers_presence(self):
        missing = []
        for h in ("from", "subject", "date", "message-id"):
            if not self.email.all_headers.get(h):
                missing.append(h)
        if missing:
            self._add_finding("medium", "Missing standard headers",
                              f"Email is missing: {', '.join(missing)}. "
                              f"Common in machine-generated phishing.", 5)

    def _check_ip_literals_in_headers(self):
        ip_re = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
        suspicious = []
        for name in ("received", "received-spf", "x-originating-ip"):
            values = self.email.all_headers.get(name)
            if not values:
                continue
            for val in values:
                found = list(set(ip_re.findall(val)))
                if found:
                    suspicious.extend(found)
        # Only flag public-range IPs (not 127./10./192.168./172.16.)
        flagged = [ip for ip in suspicious if not self._is_private(ip)]
        if flagged:
            self._add_finding(
                "medium", "Suspicious IP references",
                f"Public IP address(es) found in routing headers: {', '.join(sorted(set(flagged))[:5])}",
                5,
            )

    @staticmethod
    def _is_private(ip: str) -> bool:
        try:
            parts = [int(p) for p in ip.split(".")]
        except (ValueError, TypeError):
            return True
        return (parts[0] == 10 or
                parts[0] == 127 or
                (parts[0] == 192 and parts[1] == 168) or
                (parts[0] == 172 and 16 <= parts[1] <= 31) or
                (parts[0] == 0))
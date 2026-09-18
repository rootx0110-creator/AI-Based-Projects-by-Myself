import re
from urllib.parse import urlparse, unquote


class URLAnalyzer:
    """Extract and classify embedded URLs using local heuristics."""

    SUSPICIOUS_TLDS = {
        ".xyz", ".top", ".club", ".gq", ".tk", ".ml", ".cf", ".ga",
        ".biz", ".info", ".work", ".link", ".click", ".country", ".stream",
    }

    HIGH_RISK_KEYWORDS = [
        "login", "signin", "verify", "account", "secure", "update", "confirm",
        "wallet", "invoice", "password", "credential", "auth", "identity",
        "webscr", "paypal", "amazon", "apple", "microsoft", "netflix",
    ]

    def __init__(self, urls: list):
        self.urls = urls or []

    def analyze(self) -> dict:
        results = []
        evidence = []
        for url in self.urls:
            res = self._classify(url)
            results.append(res)
            if res["classification"] != "benign":
                evidence.append({
                    "source": "url",
                    "label": f"URL: {url[:80]}",
                    "detail": "; ".join(res["threats"]) or res["classification"],
                    "weight": 35,
                    "severity": "high" if res["classification"] == "malicious" else "medium",
                })
        return {"results": results, "evidence": evidence, "count": len(results)}

    # ------------------------------------------------------------------ #
    def _classify(self, url: str) -> dict:
        base = {"url": url, "classification": "benign", "threats": [], "reasons": []}
        decoded = self._decode_obfuscation(url)
        if decoded != url:
            base["reasons"].append(f"Obfuscated encoding decoded to: {decoded}")
            base["threats"].append("URL obfuscation detected")

        parsed = urlparse(decoded)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()

        if not host:
            base["classification"] = "suspicious"
            base["threats"].append("No resolvable hostname")
            base["reasons"].append("URL has no hostname")
            return base

        # --- threats ---
        if scheme not in ("http", "https", "ftp"):
            base["threats"].append(f"Non-standard scheme '{scheme}'")
        if scheme == "http":
            base["reasons"].append("Uses plain HTTP (not HTTPS)")
            base["threats"].append("Insecure transport")
        if not scheme:
            base["reasons"].append("Missing URL scheme")

        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            base["threats"].append("IP-address hostname")
            base["reasons"].append("Host is a raw IP address")

        if "@" in decoded.split("://", 1)[-1]:
            base["threats"].append("'@' sign redirect trick")
            base["reasons"].append("URL contains @ which redirects to a different host")

        tld_match = re.search(r"\.([a-z]{2,63})$", host)
        if tld_match:
            tld = "." + tld_match.group(1)
            if tld in self.SUSPICIOUS_TLDS:
                base["threats"].append(f"Risky top-level domain {tld}")
                base["reasons"].append(f"TLD {tld} is commonly abused by phishers")

        # keyword-stuffed host or brand impersonation
        brand = self._brand_impersonation(host)
        if brand:
            base["threats"].append(f"Suspected impersonation of '{brand}'")
            base["reasons"].append(f"Host '{host}' contains brand token '{brand}'")

        keyword_hits = [k for k in self.HIGH_RISK_KEYWORDS
                        if k in (host + (parsed.path or "").lower())]
        if keyword_hits:
            base["reasons"].append(f"Security-sensitive keywords: {', '.join(keyword_hits[:4])}")

        sub_parts = host.split(".")
        if len(sub_parts) > 4:
            base["threats"].append("Excessively deep subdomain chain")
            base["reasons"].append("Host has more than 4 dot-separated parts")

        # length: extremely long hostname
        if len(host) > 60:
            base["reasons"].append("Very long hostname")

        # --- classification ---
        if base["threats"]:
            triggers = ("IP-address hostname", "Suspected impersonation",
                        "'@' sign redirect trick", "URL obfuscation detected",
                        "Risky top-level domain")
            base["classification"] = "malicious" if any(
                t in threat for threat in base["threats"] for t in triggers
            ) else "suspicious"
        return base

    # ------------------------------------------------------------------ #
    @staticmethod
    def _decode_obfuscation(url: str) -> str:
        out = url
        for _ in range(3):
            try:
                new = unquote(out)
            except Exception:
                break
            if new == out:
                break
            out = new
        return out

    @staticmethod
    def _brand_impersonation(host: str) -> str | None:
        brands = [
            "paypal", "amazon", "appleid", "apple", "microsoft", "office365",
            "outlook", "google", "gmail", "netflix", "facebook", "linkedin",
            "dropbox", "icloud", "bankofamerica", "wellsfargo", "chase",
            "ebay", "coinbase", "binance", "payoneer", "stripe",
        ]
        full = host.lower().replace("-", "").replace("_", "")
        for b in brands:
            if b in full:
                return b
        return None
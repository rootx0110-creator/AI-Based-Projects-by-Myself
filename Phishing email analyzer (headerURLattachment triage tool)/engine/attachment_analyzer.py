import hashlib
import os
from pathlib import PurePath


class AttachmentAnalyzer:
    DANGEROUS_EXT = {
        ".exe", ".scr", ".bat", ".cmd", ".com", ".pif", ".msi", ".vbs",
        ".vbe", ".js", ".jse", ".wsf", ".wsh", ".ps1", ".hta", ".lnk",
        ".docm", ".asm", ".cpl", ".jar", ".reg", ".apk", ".msix", ".appx",
    }

    SUSPICIOUS_EXT = {
        ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".rtf", ".iso", ".img",
        ".dll", ".ocx", ".sys", ".html", ".htm", ".svg", ".xll", ".tmp",
    }

    def __init__(self, attachments: list):
        self.attachments = attachments or []

    # ------------------------------------------------------------------ #
    def analyze(self) -> dict:
        results = []
        evidence = []
        for att in self.attachments:
            res = self._classify(att)
            results.append(res)
            if res["classification"] == "malicious":
                evidence.append({
                    "source": "attachment",
                    "label": f"Attachment: {res['filename']}",
                    "detail": "; ".join(res["threats"]) or res["classification"],
                    "weight": 40,
                    "severity": "high",
                })
            elif res["classification"] == "suspicious":
                evidence.append({
                    "source": "attachment",
                    "label": f"Attachment: {res['filename']}",
                    "detail": "; ".join(res["threats"]) or res["classification"],
                    "weight": 20,
                    "severity": "medium",
                })
        return {"results": results, "evidence": evidence, "count": len(results)}

    # ------------------------------------------------------------------ #
    def _classify(self, att: dict) -> dict:
        filename = att["filename"]
        content_type = att["content_type"]
        payload = att.get("payload") or b""

        sha256, md5 = self._hashes(payload)
        ext = PurePath(filename).suffix.lower()

        res = {
            "filename": filename,
            "content_type": content_type,
            "size": att["size"],
            "extension": ext or "(none)",
            "sha256": sha256,
            "md5": md5,
            "classification": "benign",
            "threats": [],
            "reasons": [],
        }

        if ext in self.DANGEROUS_EXT:
            res["classification"] = "malicious"
            res["threats"].append(f"Dangerous executable extension '{ext}'")
            res["reasons"].append("Extension is a recognized executable / script carrier")

        elif ext in self.SUSPICIOUS_EXT:
            res["classification"] = "suspicious"
            res["threats"].append(f"Watch-listed extension '{ext}'")
            res["reasons"].append("Extension often abused in document-based phishing")

        # double extension trick: invoice.pdf.exe
        dot_count = filename.count(".")
        if dot_count > 1 and ext in self.DANGEROUS_EXT:
            res["threats"].append("Double extension detected (disguised file)")
            res["reasons"].append(f"Filename '{filename}' has {dot_count} dots; final ext hides the true type")
            res["classification"] = "malicious"

        # executable inside archives already hidden — note not detected here.

        # unexecutable raw content mime vs extension mismatch
        if ext in self.DANGEROUS_EXT and content_type.startswith("text/"):
            pass  # common, already flagged

        if payload and ext not in self.DANGEROUS_EXT and ext not in self.SUSPICIOUS_EXT and content_type.startswith("text/"):
            snippet = payload[:512].decode("utf-8", "replace").lower()
            if any(k in snippet for k in ("<script", "powershell", "cmd.exe", "createobject('wscript", "eval(")):
                res["threats"].append("Embedded script-like content")
                res["reasons"].append("Text attachment contains script/command signatures")
                res["classification"] = "malicious"

        return res

    # ------------------------------------------------------------------ #
    @staticmethod
    def _hashes(payload: bytes):
        if not payload:
            return "-", "-"
        return hashlib.sha256(payload).hexdigest(), hashlib.md5(payload).hexdigest()
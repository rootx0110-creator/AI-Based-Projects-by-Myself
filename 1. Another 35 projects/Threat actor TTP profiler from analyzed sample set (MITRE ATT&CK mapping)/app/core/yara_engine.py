"""Optional YARA integration.

Uses ``yara-python`` when installed. If it is missing, the engine falls back
to a lightweight pseudo-YARA matcher that only supports simple string literals
and the ``$a*``/``$a`` wildcard conventions, so the bundled rules still yield
hits without the native dependency.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

from .model import SampleResult

_BUNDLED_RULES = os.path.join(os.path.dirname(__file__), "..", "data", "yara", "samples.yar")


class YaraEngine:
    """Thin wrapper around native yara (or the pseudo matcher)."""

    def __init__(self, rules_path: str = _BUNDLED_RULES, use_native: bool = True):
        self.rules_path = rules_path
        self.native = None
        self.native_available = False
        self._rules: List[dict] = []
        self.error = None
        try:
            if use_native:
                import yara  # noqa: PLC0415

                self.native = yara.compile(rules_path)
                self.native_available = True
        except Exception as exc:
            self.error = "yara-python unavailable (%s); using pseudo matcher." % exc
            self._load_pseudo_rules()

    # ------------------------------------------------------------------
    @property
    def is_native(self) -> bool:
        return self.native_available

    def _load_pseudo_rules(self) -> None:
        try:
            with open(self.rules_path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except (OSError, TypeError):
            return
        for block in text.split("rule ")[1:]:
            # crude parse: rule name
            name = block.split("{", 1)[0].strip().split()[0]
            content = block.split("{", 1)[1] if "{" in block else ""
            if "strings:" not in content:
                continue
            strings_part = content.split("strings:")[1].split("condition:")[0]
            literals = re.findall(r'"((?:[^"\\]|\\.)*)"', strings_part)
            self._rules.append({
                "name": name,
                "literals": literals,
                "count": len(literals),
            })
        self._rules.sort(key=lambda r: r["count"], reverse=True)

    def match(self, sample: SampleResult) -> List[str]:
        """Return a list of matched rule names."""
        hits: List[str] = []
        raw = self._read_sample(sample)
        if self.native_available:
            try:
                matches = self.native.match(data=raw)
                return sorted(set(m.rule for m in matches))
            except Exception:
                return hits
        # pseudo matcher
        text = raw.decode("latin-1", "ignore")
        for rule in self._rules:
            if all(lit.lower() in text.lower() for lit in rule["literals"][:6]):
                hits.append(rule["name"])
        return sorted(set(hits))

    @staticmethod
    def _read_sample(sample: SampleResult) -> bytes:
        try:
            with open(sample.filepath, "rb") as fh:
                return fh.read()
        except OSError:
            return b""

    def compile_user_rules(self, path: str) -> List[str]:
        """Compile a user supplied rule set (native only). Returns rule names."""
        if not self.native_available:
            self._rules = []
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            for block in text.split("rule ")[1:]:
                name = block.split("{", 1)[0].strip().split()[0]
                self._rules.append({"name": name, "literals": [], "count": 0})
            return [r["name"] for r in self._rules]
        try:
            rules = self.native.compile(path)
            names = [r.rule for r in rules.rules]
            self.native = rules
            self.rules_path = path
            return names
        except Exception as exc:
            raise ValueError("Failed to compile YARA rules: %s" % exc)


def load_rules_meta(path: str) -> List[str]:
    """Return rule names defined in a yara file (best-effort, text based)."""
    names = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = re.match(r"^\s*rule\s+(\w+)", line)
                if m:
                    names.append(m.group(1))
    except OSError:
        pass
    return names
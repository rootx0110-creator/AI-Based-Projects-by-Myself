"""Evaluator: executes a rule's check_spec against a platform context.

Supported check_spec kinds (all strictly read-only):
  registry        - read one Windows registry value
  registry_key    - existence of a registry key
  command         - run a command, compare stdout (regex / contains / exact)
  powershell      - run a PowerShell snippet, compare output
  service         - check service state (running / stopped / startup type)
  file_exists     - presence of a file
  file_content    - regex / contains against a text file
  package         - package/app presence (platform dependent)

Expected-value kinds: exact | regex | min | max | one_of | not_contains |
in (substring) | exists | not_exists | equals_bool
"""

from __future__ import annotations

import re
from typing import Any, Optional

from .contexts import PlatformContext
from .exceptions import CheckExecutionError
from .models import Evidence, ResultStatus, Rule


class Evaluator:
    """Stateless evaluator bound to a platform context."""

    def __init__(self, context: PlatformContext) -> None:
        self.ctx = context

    # ------------------------------------------------------------------ API
    def evaluate(self, rule: Rule) -> tuple[ResultStatus, str, Any, Any, list[Evidence]]:
        """Return (status, message, observed, expected, evidence) for a rule."""
        spec = rule.check_spec
        kind = str(spec.get("kind", "")).lower()
        handler = getattr(self, f"_check_{kind}", None)
        if handler is None:
            raise CheckExecutionError(f"unknown check kind: {kind!r}")

        observed, evidence = handler(spec)
        expected = spec.get("expected")

        if observed is None and spec.get("allow_missing", False):
            return (
                ResultStatus.NOT_APPLICABLE,
                "Check target not present on this system.",
                None,
                expected,
                evidence,
            )

        ok, message = self._compare(observed, spec)
        status = ResultStatus.PASS if ok else ResultStatus.FAIL
        if not ok and not message:
            message = "Configuration does not meet the expected value."
        if ok:
            message = message or "Compliant."
        return status, message, observed, expected, evidence

    # ------------------------------------------------------------ comparison
    @staticmethod
    def _compare(observed: Any, spec: dict[str, Any]) -> tuple[bool, str]:
        expected = spec.get("expected")
        exp_kind = str(spec.get("expected_kind", "exact")).lower()
        fail_msg = str(spec.get("fail_message", "")).strip()

        if expected is None and exp_kind in {"exists", "not_exists"}:
            ok = bool(observed) if exp_kind == "exists" else not observed
            return ok, ""

        if exp_kind == "exact":
            ok = _norm(observed) == _norm(expected)
        elif exp_kind == "equals_bool":
            ok = _as_bool(observed) == bool(expected)
        elif exp_kind == "regex":
            ok = re.search(str(expected), _norm(observed), re.IGNORECASE) is not None
        elif exp_kind == "in":
            ok = str(expected).lower() in _norm(observed).lower()
        elif exp_kind == "not_contains":
            ok = str(expected).lower() not in _norm(observed).lower()
        elif exp_kind == "one_of":
            opts = [str(o).lower() for o in spec.get("options", [])]
            ok = _norm(observed).lower() in opts
        elif exp_kind in {"min", "max"}:
            o = _as_number(observed)
            e = _as_number(expected)
            if o is None or e is None:
                return False, f"non-numeric observed value: {observed!r}"
            ok = o >= e if exp_kind == "min" else o <= e
        elif exp_kind == "exists":
            ok = bool(observed)
        elif exp_kind == "not_exists":
            ok = observed in (None, "", [], False)
        else:
            raise CheckExecutionError(f"unknown expected_kind: {exp_kind!r}")

        if not ok and fail_msg:
            return ok, fail_msg
        return ok, ""

    # ------------------------------------------------------------- handlers
    # Each handler returns (observed_value, evidence_list).

    def _check_registry(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        hive = spec["hive"]
        path = spec["path"]
        value = spec["value"]
        raw = self.ctx.registry_value(hive, path, value)
        ev = Evidence(
            source="registry",
            detail=f"{hive}\\{path}\\{value}",
            raw=repr(raw) if raw is not None else "<not set>",
        )
        return raw, [ev]

    def _check_registry_key(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        hive, path = spec["hive"], spec["path"]
        exists = self.ctx.registry_key_exists(hive, path)
        ev = Evidence(source="registry", detail=f"{hive}\\{path}", raw=str(exists))
        return exists, [ev]

    def _check_command(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        cmd = spec["command"]
        timeout = float(spec.get("timeout", 15))
        code, out, err = self.ctx.run_command(cmd, timeout=timeout)
        ev = Evidence(
            source="command",
            detail=" ".join(cmd),
            raw=(out or err).strip()[:2000],
            truncated=len(out) > 2000,
        )
        capture = str(spec.get("capture", "stdout"))
        observed = out if capture == "stdout" else err
        if spec.get("json_line") and observed.strip():
            import json  # noqa: PLC0415

            try:
                observed = json.loads(observed.strip().splitlines()[-1])
            except ValueError:
                pass
        return observed.strip(), [ev] if observed.strip() else [ev]

    def _check_powershell(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        script = spec["script"]
        timeout = float(spec.get("timeout", 30))
        code, out, err = self.ctx.run_powershell(script, timeout=timeout)
        text = (out or err).strip()
        ev = Evidence(source="powershell", detail=script[:300], raw=text[:2000])
        observed: Any = text
        if spec.get("as_bool"):
            observed = text.lower() in {"true", "1"}
        elif spec.get("as_float"):
            try:
                observed = float(re.findall(r"-?\d+(?:\.\d+)?", text)[0])
            except (IndexError, ValueError):
                observed = None
        elif spec.get("as_int"):
            try:
                observed = int(re.findall(r"-?\d+", text)[0])
            except (IndexError, ValueError):
                observed = None
        return observed, [ev]

    def _check_service(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        name = spec["service"]
        state = self.ctx.service_status(name)
        ev = Evidence(
            source="service", detail=name, raw=state or "<service not found>"
        )
        return state, [ev]

    def _check_file_exists(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        path = spec["path"]
        exists = self.ctx.file_exists(path)
        return exists, [Evidence(source="file", detail=path, raw=str(exists))]

    def _check_file_content(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        path = spec["path"]
        try:
            text = self.ctx.read_file_text(path)
        except CheckExecutionError:
            return None, [Evidence(source="file", detail=path, raw="<missing>")]
        pattern = spec.get("pattern")
        if pattern:
            found = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            observed = found.group(0) if found else ""
        else:
            observed = text.strip()
        ev = Evidence(
            source="file", detail=path, raw=observed[:2000] if observed else "<no match>"
        )
        return observed, [ev]

    def _check_package(self, spec: dict[str, Any]) -> tuple[Any, list[Evidence]]:
        installed = self.ctx.package_installed(spec["package"])
        return installed, [
            Evidence(source="package", detail=spec["package"], raw=str(installed))
        ]


# ----------------------------------------------------------------- helpers
def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value).lower() in {"1", "true", "yes", "enabled", "on"}


def _as_number(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


__all__ = ["Evaluator"]

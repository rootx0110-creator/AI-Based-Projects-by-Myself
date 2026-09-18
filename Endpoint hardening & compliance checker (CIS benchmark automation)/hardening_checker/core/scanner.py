"""Scanner: loads rules, evaluates them read-only, and assembles a report."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import time
import uuid
from typing import Callable, Optional

from .contexts import IS_WINDOWS, PlatformContext, make_context, utc_now_iso
from .exceptions import CheckExecutionError, RuleLoadError
from .models import (
    CheckResult,
    PlatformInfo,
    Profile,
    ResultStatus,
    Rule,
    ScanReport,
    ScanSummary,
)
from .scoring import compute_score


def load_rules(platform_filter: str) -> list[Rule]:
    """Import hardening_checker.rules.* and collect their Rule objects.

    Rule modules expose a module-level function `get_rules() -> list[Rule]`.
    """
    from .. import rules as rules_pkg  # noqa: PLC0415

    collected: list[Rule] = []
    seen: set[str] = set()

    for mod_info in pkgutil.iter_modules(rules_pkg.__path__):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"hardening_checker.rules.{mod_info.name}")
        getter = getattr(module, "get_rules", None)
        if not callable(getter):
            continue
        for rule in getter():
            if not isinstance(rule, Rule):
                raise RuleLoadError(
                    f"{mod_info.name}: get_rules() returned a non-Rule object"
                )
            if rule.rule_id in seen:
                raise RuleLoadError(f"duplicate rule id: {rule.rule_id}")
            seen.add(rule.rule_id)
            if platform_filter in rule.platforms:
                collected.append(rule)

    collected.sort(key=lambda r: (r.category, r.rule_id))
    return collected


class Scanner:
    """Runs rules against a platform context and produces a ScanReport."""

    def __init__(
        self,
        context: Optional[PlatformContext] = None,
        progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        self.ctx = context or make_context()
        self.progress = progress or (lambda *_: None)

    # ------------------------------------------------------------------ API
    def scan(
        self,
        profile: Profile = Profile.L1,
        include_manual: bool = False,
        include_info: bool = True,
    ) -> ScanReport:
        if isinstance(profile, str):
            profile = Profile(profile)
        started = utc_now_iso()
        t0 = time.perf_counter()

        platform_info = self.ctx.platform_info()
        self._info = platform_info
        rules = load_rules(self.ctx.name)
        rules = [
            r
            for r in rules
            if r.profile is profile or profile is Profile.L2 and r.profile is Profile.L1
        ]
        if not include_info:
            rules = [r for r in rules if r.severity.value != "info"]

        from .evaluator import Evaluator  # noqa: PLC0415

        evaluator = Evaluator(self.ctx)
        results: list[CheckResult] = []

        for idx, rule in enumerate(rules, start=1):
            self.progress(rule.rule_id, idx, len(rules))
            results.append(self._evaluate_rule(rule, evaluator, include_manual))

        finished = utc_now_iso()
        summary = ScanSummary()
        summary.recompute(results)
        score, grade = compute_score(results)

        return ScanReport(
            scan_id=uuid.uuid4().hex[:12].upper(),
            started_at=started,
            finished_at=finished,
            profile=profile.value,
            platform=platform_info,
            results=results,
            summary=summary,
            score=score,
            grade=grade,
            duration_seconds=round(time.perf_counter() - t0, 2),
        )

    # ------------------------------------------------------------ internals
    def _evaluate_rule(
        self, rule: Rule, evaluator, include_manual: bool
    ) -> CheckResult:
        ts = utc_now_iso()
        t0 = time.perf_counter()

        if rule.manual and not include_manual:
            return CheckResult(
                rule=rule,
                status=ResultStatus.MANUAL,
                message="Manual verification required (skipped automatically).",
                timestamp=ts,
            )

        if rule.requires_admin and not getattr(self, "_info", PlatformInfo()).is_admin:
            return CheckResult(
                rule=rule,
                status=ResultStatus.SKIPPED,
                message="Skipped: requires administrator privileges.",
                timestamp=ts,
            )

        try:
            status, message, observed, expected, evidence = evaluator.evaluate(rule)
        except CheckExecutionError as exc:
            return CheckResult(
                rule=rule,
                status=ResultStatus.ERROR,
                message=f"Check could not run: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
                timestamp=ts,
            )
        except Exception as exc:  # noqa: BLE001 - one bad rule must not kill a scan
            return CheckResult(
                rule=rule,
                status=ResultStatus.ERROR,
                message=f"Unexpected evaluator error: {exc!r}",
                duration_ms=(time.perf_counter() - t0) * 1000,
                timestamp=ts,
            )

        return CheckResult(
            rule=rule,
            status=status,
            message=message,
            observed=observed,
            expected=expected,
            evidence=evidence,
            duration_ms=(time.perf_counter() - t0) * 1000,
            timestamp=ts,
        )


__all__ = ["Scanner", "load_rules", "PlatformInfo"]

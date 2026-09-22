"""Headless smoke test for the C2 Detection Lab core pipeline.

Exercises: signatures generation, C2 server + beacon client live capture,
detection analysis, HTML report rendering and JSON export. Run with:

    python -m c2lab.selftest
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from . import __version__
from .presets import get_profile, profile_names


def test_signatures() -> None:
    from .signatures import build_all_rules

    for name in profile_names():
        rules = build_all_rules(get_profile(name))
        assert len(rules) == 3, "expected 3 artifacts per profile"
        for key in ("c2_beacons.rules", "c2_beacons.sig", "beacon_detect.zeek"):
            assert rules[key].strip(), f"{name}: {key} empty"
    print("[OK] signature generation for", len(profile_names()), "profiles")


def test_live_session() -> None:
    from .client import BeaconClient
    from .server import C2Server

    server = C2Server("127.0.0.1", 18280)
    assert server.start(), f"server failed: {server.error}"
    profile = get_profile("Sliver HTTPS")
    client = BeaconClient(server, profile, 1, 20.0, 6)
    client.start()
    try:
        time.sleep(8)
    finally:
        client.stop()
        server.stop()
    events = server.snapshot()
    assert events, "no beacons captured"
    print(f"[OK] live session: {len(events)} beacons captured from {profile.name}")
    assert all(e.user_agent == profile.user_agent for e in events), "UA mismatch"
    assert len({e.user_agent_hash for e in events}) == 1, "UA hash should be stable"
    return events


def test_detection(events) -> None:
    from .detect import analyze_session
    from .signatures import build_all_rules

    profile = get_profile("Sliver HTTPS")
    result = analyze_session(events, profile)
    result.generated_at = "2026-01-01T00:00:00Z"
    result.rule_texts = build_all_rules(profile)
    assert result.total_events == len(events)
    assert any(f.rule.startswith("suricata") for f in result.findings), "expected Suricata findings"
    assert result.qualified, "expected a positive verdict"
    print(f"[OK] detection: {len(result.findings)} findings, verdict='{result.verdict}'")
    return result


def test_report(result) -> None:
    from .report import save_report, render_full, render_summary, render_html

    full = render_html(result, "full")
    summ = render_html(result, "summary")
    assert "<!DOCTYPE html>" in full and "Detection Findings" in full
    assert "<!DOCTYPE html>" in summ and "Detection Findings" in summ
    target = Path("outputs/selftest_report.html")
    save_report(result, target)
    assert target.exists() and target.stat().st_size > 10_000
    print(f"[OK] html report render: full={len(full)}B summary={len(summ)}B saved={target}")
    return target


def test_rules_export(result, target) -> None:
    from .report import export_events_as_json

    for name, content in result.rule_texts.items():
        (Path("outputs/selftest_rules") / name).parent.mkdir(parents=True, exist_ok=True)
        (Path("outputs/selftest_rules") / name).write_text(content, encoding="utf-8")
    json_target = export_events_as_json(result.events, Path("outputs/selftest_events.json"))
    assert json_target.exists()
    print("[OK] rules + json export")


def main() -> int:
    print(f"C2 Detection Lab self-test (v{__version__})")
    test_signatures()
    events = test_live_session()
    result = test_detection(events)
    target = test_report(result)
    test_rules_export(result, target)
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
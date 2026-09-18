"""End-to-end scan over the FakeContext, plus report rendering smoke tests."""

from __future__ import annotations

import json

from hardening_checker.core.models import Profile
from hardening_checker.core.scanner import Scanner
from hardening_checker.reporting import render_html, render_pdf


def test_full_scan_e2e(fake_ctx):
    scanner = Scanner(context=fake_ctx)
    report = scanner.scan(profile=Profile.L1)

    assert report.summary.total >= 40
    assert 0.0 <= report.score <= 100.0
    assert report.grade
    assert report.scan_id
    statuses = {r.status.value for r in report.results}
    assert statuses  # non-empty
    # fake ctx passes FilterAdministratorToken + RunAsPPL + net accounts policy
    passed = {r.rule.rule_id for r in report.results if r.status.value == "pass"}
    assert "HC-WIN-0101" in passed
    assert "HC-WIN-0001" in passed


def test_scan_reports_progress(fake_ctx):
    seen = []
    scanner = Scanner(context=fake_ctx,
                      progress=lambda rid, i, n: seen.append((rid, i, n)))
    scanner.scan(profile=Profile.L1)
    assert seen and seen[-1][1] == seen[-1][2]  # reaches total


def test_html_report_renders(fake_ctx, tmp_path):
    report = Scanner(context=fake_ctx).scan(profile=Profile.L1)
    out = render_html(report, tmp_path / "r.html")
    text = out.read_text(encoding="utf-8")
    assert "Compliance Report" in text
    assert report.platform.hostname in text
    assert "HC-WIN-" in text


def test_pdf_report_renders(fake_ctx, tmp_path):
    report = Scanner(context=fake_ctx).scan(profile=Profile.L1)
    out = render_pdf(report, tmp_path / "r.pdf")
    data = out.read_bytes()
    assert data[:5] == b"%PDF-"
    assert len(data) > 5000


def test_cli_json_roundtrip(fake_ctx, tmp_path, monkeypatch):
    from hardening_checker.cli import main

    json_path = tmp_path / "out.json"
    html_path = tmp_path / "out.html"
    pdf_path = tmp_path / "out.pdf"

    # Monkeypatch make_context so the CLI uses the fake context.
    import hardening_checker.cli as cli_mod

    monkeypatch.setattr(cli_mod, "make_context", lambda: fake_ctx)

    rc = cli_main_safe([
        "scan", "--profile", "l1",
        "--json", str(json_path),
        "--html", str(html_path),
        "--pdf", str(pdf_path),
        "--quiet",
    ], cli_mod)
    assert rc in (0, 1)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["platform"]["hostname"] == "TEST-BOX"
    assert data["summary"]["total"] >= 40
    assert html_path.exists() and pdf_path.exists()


def cli_main_safe(argv, cli_mod):
    return cli_mod.main(argv)

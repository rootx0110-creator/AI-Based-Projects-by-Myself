# MEMORY.md — working notes & history

## Session purpose
Build a "Enterprise cybersecurity policy generator" that takes an
interview and produces a board-ready policy document, as a desktop
EXE or web app, with an awesome UI and HTML report download.

## Key decisions (and why)
1. **Static single-file SPA** (no framework, no build).
   Why: zero-dependency, runs offline, trivially wrapped into an
   EXE by pywebview. Board/material confidentiality is protected.
2. **Fake "AI" via parameterised expert templates**, not a remote LLM.
   Why: works offline, deterministic, auditable; an LLM backend can
   swap in later behind the same `PolicyEngine` API.
3. **Board-ready = layered language.** Executive summary decoded for
   directors; policy body balanced between plain English and control
   detail an auditor can check.
4. **Risk is quantised.** 1-5 posture ratings x target assurance =>
   residual risk + gap actions. Posture ratings drive *which*
   remedial clauses appear in each chapter.
5. **Regulator pick is automatic** from sector/geo/payments, with a
   manual override in settings.
6. **Report export is static HTML with embedded CSS only** (no JS).
   Safe to email, printable, page-break aware.
7. **All user data lives in localStorage** — no server, no telemetry.

## Patterns / conventions
- Naming: `view.*`, `ui.*`, `eng.*` namespaces; camelCase.
- Chapter factory signature: `({answers, model, fw}) => {id, num, title, sections[]}`
- Sentence builders embed variables via `tpl` template strings.
- Every generated report includes metadata + version-history table.

## History
- 2026-09-22  Scaffolded docs; built index.html (wizard + engine +
              preview); added HTML report download; added pywebview
              wrapper + build_exe.ps1; smoke-tested in browser.
- 2026-09-22  v1.0 tagged STABLE (see state.md).

## Open questions
- Should downloadable "Word/DOCX" export be added? (roadmap todo)
- Kick off a "report bundle" that also generates a one-page
  executive slide deck (HTML slide)? (roadmap todo)
- GDPR/DSR templates could be included as annexes. (backlog)
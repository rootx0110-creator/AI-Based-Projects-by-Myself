# State

## Working
- [x] SQLite store with seeded challenges (9), hint_log, settings
- [x] Progressive hint flow: authored -> AI -> local category fallback
- [x] AI providers: OpenAI-compatible + Anthropic, urllib only, 45s timeout
- [x] AI settings page with Test Connection
- [x] Flag verification + manual solve + add-challenge trainer tools
- [x] HTML report preview + Content-Disposition download
- [x] Dashboard stats (categories, solved, hints, latest activity)
- [x] start.bat launcher, build_exe.py (one-file EXE), docs

## Verified
- Python mode: seed scan, hint endpoint (authored + local), verify, markSolved,
  settings persist, report generation/download.
- EXE mode: builds, launches, serves UI, scan/report endpoints answered.

## Not yet / blocked
- Real LLM round-trip (no API key in this environment) — Test Connection flow
  is in place; fallback path is proven.
- Multi-user trainee tracking / cohorts (planned in memory.md).

## Known limits
- Flags in plaintext (lab use only; hashing is a planned toggle).
- Single-trainee progress model (no per-user separation yet).
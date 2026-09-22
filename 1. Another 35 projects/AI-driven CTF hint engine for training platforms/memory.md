# Memory

## Decisions made
- Web app over desktop GUI: Flask + browser UI reuses the trainee's existing
  browser and makes the HTML report/download trivially shareable.
- SQLite via stdlib (no DB server) so the app and the EXE are truly portable.
- AI calls use urllib only -> zero third-party HTTP deps inside ai_engine.py.
- Progressive disclosure: prepared hints first, AI coach after. This keeps the
  out-of-box experience deterministic for trainers while showcasing real AI.
- Port selection: random free port in 8800-9999 because several lab projects
  already occupy 5000/8090 etc. Browser auto-opens.
- Frozen EXE stores user data in a `data\` folder next to the EXE, while the
  bundled templates/static are served from the PyInstaller _MEIPASS dir.

## Gotchas learned
- When frozen, `__file__` points INSIDE the extraction dir (_MEIPASS). Anything
  user-persisted must anchor to `sys.executable`'s folder, not `__file__`.
- PyInstaller onefile spawns a child process on Windows; probing listeners by
  parent PID is unreliable — scan ports instead.
- Emoji/unicode in hint text must be escaped client-side before innerHTML.

## Status
- Core engine, seeding, solve flow, reports, EXE build all verified.
- AI path verified structurally (test connection), realistic API keys not
  available in this environment — fallback path is the default here.

## Next
- Optional flag hashing setting (trainer toggle: plain vs sha256 compare).
- Export/import challenge packs as JSON in /settings.
- Multi-user sessions (session id per trainee) for cohort reporting.
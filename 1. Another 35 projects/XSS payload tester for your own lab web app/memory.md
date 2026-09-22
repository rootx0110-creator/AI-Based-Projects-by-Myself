# Memory

Session-scoped facts the app works from (kept in code, not a DB).

## Runtime state
- `_last_report` in `app.py`:
  `{ "token": ..., "html": ... }` - the most recent generated
  report, so `/api/report/<token>` can serve it again. Cleared on
  restart (process memory only).
- Flask dev server is `threaded=True`; no external cache/DB.
- `requests.Session` is created per-scan (not shared) so headers /
  cookies never leak between different targets.

## Assumptions verified at build time
1. Engine decodes the payload into 5 variants and the response
   body into 5 variants; the cross-product catches URL-encoding,
   HTML-entity encoding, and JS unicode escapes (\u006c etc.).
   Verified against the sample lab: obfuscated payloads score
   "Executable XSS" when the app also echoes the enclosing tag.
2. Verdicts for a plain (non-executable) scan target: info
   payloads report "Reflected", everything else reports
   "Not reflected / filtered".
3. Report generation must not crash on `%` inside inline CSS
   (escaped as `%%` because the page is `%`-formatted).

## Payload library notes
- 29 built-in payloads in 6 categories (payloads.py).
- Markers are chosen so `alert(1)` / `alert(document.domain)`
  surface as executable when a dangerous sink is also present.
- `Scanner` payloads (I001/I002, P004) are non-executable probes
  used to map where input echoes back.

## Things to remember when editing
- Keep all UI-facing values JSON-safe (engine output is
  json.dumps-able; validated during testing).
- Never send raw HTML to the browser: `static/app.js` escapes
  everything before injection; `report.py` uses `html.escape`.
- The report endpoint re-uses the run object the client already
  has, so a scan never has to be re-executed for the download.
- Port 5173 is the Flask default in app.py (changeable via --port).
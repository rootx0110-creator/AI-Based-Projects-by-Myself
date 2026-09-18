# State — Web App Fuzzer for Input Validation Testing

> Version 1.0.0 · September 2026

## 1. Current status

The fuzzer is **feature-complete for v1.0.0** and runs as a local web
application (`python app.py` then open the printed URL).

## 2. What works today

### Scanning
- Single-target fuzzing against **GET / POST / PUT / PATCH / DELETE / HEAD**.
- Field injection into query parameters, form body, or custom headers
  (configurable per scan).
- Cookie and custom header support with a configurable user-agent.
- 1–12 worker threads, optional request delay, configurable per-request
  timeout, TLS verification toggle (self-signed support), timing baseline probe
  and shuffled request order.

### Payload library (11 categories, ~140 payload/technique pairs)
- SQL injection (boolean, union, error, time-based, obfuscation)
- Cross-site scripting (reflected, mutation, external, attribute)
- Command injection (marker, time-delay, newline)
- Path traversal / local file inclusion (encoded, double/multi encoded, Windows)
- LDAP injection (filter structure)
- Server-side template injection (arithmetic + RCE/leak probes)
- SSRF (localhost, cloud metadata, gopher/dict)
- XXE (file + SSRF extraction)
- Open redirect
- Format string
- JWT / auth tampering (none algorithm, role spoofing)

### Detection
- Payload **reflection** tracking per finding.
- **SQL and generic error signature** matching (regex sets).
- **Time-based** anomaly detection against an established baseline.
- **Semantic content checks** for LFI file markers, SSTI evaluation, SSRF
  redirects.
- Status-code anomaly handling (4xx, 5xx).
- Weighted risk score → severity (`high / medium / low / ok`).

### UI
- Friendly, responsive, single-page 4-step flow with live progress bar and log.
- Auto suggested payload categories per field name.
- Category bulk shortcuts (enable all / disable all / core web set) with a
  persisted selection in `localStorage`.
- Live results table with severity + text filters and expandable evidence rows.
- `Ctrl+Enter` to start a scan.

### Reporting
- Self-contained **HTML report download** from current (filtered) results via
  `POST /api/report`, or the full server copy via `GET /api/report/<token>`.
  Includes grade, severity/category breakdowns, configuration, and full
  evidence table; print-friendly.

## 3. Known limitations

1. **Read-heavy on responses, blind-out-only on some classes.** Detection is
   primarily **black-box response analysis**. Truly blind injection (no
   reflection, no content, no timing) will mostly show as "OK" unless a
   time-based delay or error text is observed.
2. **Reflection = lead, not proof.** A reflected payload is reported as
   suspicious; it does not prove an exploitable XSS (encoding/context matters).
3. **In-memory scan registry.** `SCANS` lives in process memory; a server
   restart stops scans and loses the registry. Suitable for one-off testing.
4. **No authentication flows beyond static cookies.** No login / OAuth / CSRF
   token choreography or session rotation.
5. **No crawling / discovery.** The user must supply the endpoint and field
   names manually; there is no spider or parameter enumeration.
6. **Payload scope is safety-biased.** Time-based sleeps are short (5 s) and
   nothing destructive is sent, so coverage of aggressive techniques is limited
   by design.
7. **Single-host.** The fuzzer watches one target URL per scan, not a site tree.
8. **Concurrency ceiling of 12** workers keeps load bounded on purpose.
9. **Not a credentialed DAST replacement.** Compare with tools like Burp/ZAP for
   full session handling and semi-confirmed exploitation.

## 4. Safety considerations (current)

- Binds to `127.0.0.1` by default.
- Payloads contain no file-destroying or data-modifying commands.
- Time payloads use bounded sleeps; a 2–120 s timeout prevents hangs.
- Stop button aborts pending jobs; in-flight requests complete or time out.
- UI banner reminds users the tool is for authorized testing only.

## 5. Suggested next steps (backlog)

- [ ] Header/auth session manager (login flow, token refresh).
- [ ] Match-based confirmation, e.g. base/response diffing for boolean blind.
- [ ] Payload mutations (case/encoding fuzzing on top of the base payloads).
- [ ] JSON request-body injection in addition to form data.
- [ ] Export formats: CSV / JSON / PDF alongside HTML.
- [ ] Persistent scan history across restarts (SQLite).
- [ ] Optional sighted "webhook-confirm" for blind RCE/SSRF payloads.
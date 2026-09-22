# Memory — SecuRevealer

Long-lived knowledge about this project: decisions, gotchas, environment facts.
(Read this first when resuming work.)

## Environment
- Windows host, but terminal is bash — always use POSIX syntax (`ls`, `rm`, forward slashes).
- Node.js v24.20.0 available. No package.json needed (project is dependency-free).
- Project directory started empty; everything here was created in one session.

## Key decisions (and why)
1. **Zero-dependency Node backend.** `node:http` + hand-rolled multipart parser.
   No npm install → instant start, no supply-chain surface for a *security* tool.
1b. **Exe packaging via @yao-pkg/pkg** (maintained fork of vercel/pkg; the
   original pkg is archived). Command:
   `npx -y @yao-pkg/pkg . --targets node24-win-x64 --output dist/SecuRevealer.exe`
   - package.json MUST have a `bin` field (pkg errors without it).
   - `pkg.assets: ["public/**/*"]` embeds UI + demo fixtures into the
     snapshot; fs.readFile/readdirSync are patched to read from it, so the
     existing static-serving code works unchanged inside the exe.
   - Inside the exe, `process.pkg` is truthy — server uses that flag to
     auto-open the browser (opt-out: SECUREVEALER_NO_OPEN=1).
2. **No build step / no framework.** Vanilla HTML/CSS/JS UI served statically.
   Keeps the whole thing runnable as `node backend/server.js`.
3. **Regex rules + AST validation** instead of a full parser (e.g. ESLint/Babel).
   Trade-off: breadth + zero deps over deep dataflow. Documented as a non-goal.
4. **"AI-assisted" is a local heuristic advice engine** (`aiadvice.js`): per-finding
   root cause, exploit scenario, and fix snippet. No external LLM API by default.
   It is deterministic and works offline.
5. **HTML report is fully self-contained** (inline CSS, no CDN, no JS deps) so it
   can be emailed/archived and opened offline.
6. **One browser-side fallback:** the UI can generate the report locally from scan
   JSON if the server is unreachable (same visual template).

## Gotchas
- Windows bash: never use `dir`, `del`, `copy`; use `ls`, `rm`, `cp`.
- Regex rule strings in `detectors.js` are JS regex literals — remember to escape
  `/` inside character classes and double-escape in `new RegExp` strings.
- The multipart parser is minimal: it handles standard browser `FormData`
  uploads; don't feed it chunked/streamed non-standard encodings.
- Findings carry `line`/`col` + a trimmed `snippet` (the matched line only);
  the UI viewer highlights that single line. Keep scanner output shape
  {ruleId,title,severity,cwe,owasp,line,col,snippet,match,why,exploit,
   fixSnippet,refs} consistent if you touch detectors/scanner.
- `HARDCODED_SECRET` regex uses a lookbehind `(?<![A-Za-z])` instead of `\b`
  so underscore-prefixed names (JWT_SECRET, DATABASE_PASSWORD) still match.

## Conventions
- Severity order everywhere: CRITICAL > HIGH > MEDIUM > LOW.
- Rule ids are SCREAMING_SNAKE (e.g. `SQLI_CONCAT`, `HARDCODED_SECRET`).
- Demo fixtures live in `public/demo/` (served at `/demo/...` for the UI's
  "Load demo files" button) and are intentionally insecure — never "fix"
  them; tests/UX rely on the findings they produce.

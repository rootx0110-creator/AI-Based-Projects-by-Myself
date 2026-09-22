# Architecture

## Overview
AI-Driven CTF Hint Engine is a single-process Flask web application with an
optional PyInstaller one-file EXE packaging. It is fully self-contained:
no external database service, no node_modules, only Flask + the stdlib.

```
browser / EXE window
      |
      v
   Flask app.py
      | routes
      +----> database.py (sqlite3, data\hintengine.db)
      |       challenges / hint_log / settings
      +----> ai_engine.py (make_hint, test_connection)
      |       OpenAI-compatible + Anthropic HTTP calls (urllib only)
      |       local template fallback (per category, escalating)
      +----> report.py (render_report -> standalone HTML)
      |
   templates/  Jinja2 pages
   static/     style.css, app.js
```

## Hint flow (progressive disclosure)
1. Trainee clicks "Ask for hint" on /challenge/<id>.
2. POST /api/challenge/<id>/hint:
   - level = number of hints already logged + 1
   - if level <= number of authored hints -> return authored hint (source=authored)
   - else if AI enabled + key present -> LLM call (OpenAI chat completions or
     Anthropic messages). On ANY error -> fall through to local.
   - else -> per-category local hint (source=local).
3. Hint is inserted into hint_log with timestamp; challenge flips to in_progress.
4. UI appends the new hint card; button label escalates.

## Data model
challenges(id, title, category, difficulty, description, flag, hints[]JSON,
           status[todo|in_progress|solved], source[seed|user], created_at, solved_at)
hint_log(id, challenge_id, level, source[authored|ai|local], content, created_at)
settings(key, value)  -- provider, base_url, api_key, model, enabled

## Failure handling
- AI call errors are caught; local fallback kicks in (app never breaks offline).
- Report generation is pure server-side; iframes the rendered HTML for preview
  and serves the same string as a Content-Disposition attachment for download.
- EXE/frozen mode: BASE_DIR = sys._MEIPASS (bundled templates/static),
  APP_DIR = exe directory (data\ lives next to the EXE, user-editable).

## Security notes
- Flags are stored in plaintext for lab use (see readme -> hash for production).
- API keys are stored in the local sqlite settings table (lab tool; do not
  expose the data folder).
- The server binds 127.0.0.1 only. Choose a random free port at startup to
  avoid clashing with other lab apps.
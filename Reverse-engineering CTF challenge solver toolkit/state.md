# State

Run-state and file-format notes for the toolkit.

## Application state

Deliberately **stateless**: nothing is persisted between sessions.

| State                                  | Where it lives                          | Lifetime            |
|----------------------------------------|-----------------------------------------|---------------------|
| Loaded file bytes (`current_bytes`)    | `SolverApp`                          | until another open   |
| Loaded file path (`current_path`)      | `SolverApp`                          | until another open   |
| Per-page widget values                 | page widgets (sliders, entries, checks) | session only         |
| Solver results                         | `ResultBox` widgets                     | session only         |
| Reports                                | written straight to `.html` on disk     | user-chosen location |

There is no settings file, no cache, and no registry writes. The
application writes nothing to disk except the user-requested HTML report.

## State transitions

```
start  ──► SolverApp()              (No file loaded)
              │
              ▼
        Open File ──► current_bytes, current_path set; goes to FileInfo page
              │
              ├──► any tool page: Run ──► Worker(thread) ──► page output box
              ├──► Report ──► Generate & Download ──► Save dialog ──► .html
              ▼
        Exit (WM_DELETE_WINDOW) ──► destroy(); no persistence
```

Worker lifecycle (per analysis):
`Worker(win, fn, done)` → thread runs `fn()`; result (or exception) is
queued; `after(60ms)` polls the queue; `done(result, err)` is invoked on
the main thread; exactly one of `result`/`err` is non-None.

## File formats

| Item         | Format                                                        |
|--------------|---------------------------------------------------------------|
| Document     | `architecture.md`, `memory.md` (Markdown)                     |
| Readme       | `readme.txt` (plain text)                                     |
| Reports      | HTML5, UTF-8, single file, inline `<style>` — no external refs |
| Binary input | any file; read opaque as bytes, magic-sniffed                 |

## HTML report structure

```
<!doctype html><html><head><style>… dark theme …</style></head>
<body class="wrap">
  <header>  title + target + timestamp
  <div class="cards">  stat cards (size / type / entropy / sha prefix)
  <h2> File Metadata </h2>          kv_table
  <h2> PE/ELF extras </h2>          kv_table (if detected)
  <h2> Entropy Analysis </h2>       kvs + entropy bar
  <h2> Extracted Strings </h2>      table (offset / type / value)
  <h2> Hex Dump Preview </h2>       table (offset / hex / ascii)
  <h2> Letter Frequency </h2>       table with inline bar cells
  <h2> Notable Findings </h2>       list
  <footer>  tool name + timestamp + disclaimer
</body></html>
```

## Concurrency rules (state safety)

1. One `Worker` per analysis; results queue is per-Worker.
2. UI state (widget values) is read on the main thread immediately
   before spawning the worker — the thread only reads `current_bytes`
   (immutable `bytes`).
3. `ResultBox` writes happen exclusively on the main thread.
4. `ReportPage` builds the whole HTML before any dialog is shown; the
   save dialog is modal and blocking.

## Known edge cases

- Files that look like text but contain a `{`-heavy binary column can
  defeat multi-byte XOR auto-breaking (see `memory.md`). The candidate
  list still shows plausible keys; use known-key mode for exact results.
- UTF-16 string extraction is heuristic (runs of `ascii + 0x00`), so
  genuinely encoded UTF-16 text decodes, but wide-character payloads with
  embedded NULs can be missed.
- Files ≥ 64 MiB skip full-buffer hashes and stream instead (identical
  results, just more I/O).
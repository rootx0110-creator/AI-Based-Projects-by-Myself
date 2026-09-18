# Memory Notes

Behavioural notes for maintainers and for anyone auditing the tool's
heuristics. "Memory" here means *notes to remember*, not process memory
dumps.

## Runtime constraints

- The whole challenge file is read into RAM on Open. Solver/analysis
  functions then operate on bounded samples:
  - multi-byte XOR: 4 KiB sample, key length up to the UI value (default 16)
  - single-byte XOR / known keys: 8 KiB sample
  - strings / hex / frequency: streamed or capped row/string counts
  - hashes: streamed (ms sized files use `hashlib.file_digest`)
- Keep sample caps low: the `_combined` scoring used by the XOR
  refinement is O(n) per probe and runs 256 × key-length probes.

## Scoring traps discovered (important)

1. **Column-wise English scoring misleads.** Interleaved columns of CTF
   flag text contain many `{ } _ 0-9` characters; frequency models rank
   wrong key bytes above the true ones. Always seed columns with
   `ascii_text_score` (printability), never English frequency alone.
2. **Probes must not be downsampled too far.** A 273-byte probe window is
   too noisy for the word-bonus; the refinement silently stalls at keys
   like `k$y` instead of `k3y`. Full-text (≥4 KiB) scoring fixed this.
3. **Plain-array corruption bug.** The coordinate-ascent loop originally
   only restored a column when a candidate *improved* the score; failed
   probes leaked the wrong byte into the `plain` buffer for every later
   probe. Rule: after a coordinate scan, ALWAYS rebuild the column from
   `sample[j] ^ best_byte`.
4. **Occam jitter matters.** A length-6 key `k3yk3y` that is a doubled
   correct length-3 key decrypts perfectly and scores ~equal to `k3y`.
   `score -= 0.9 * klen` keeps the minimal key on top.
5. **Long keys inflate scores.** A wrong 12-byte key frequently produces
   "mostly printable" text scoring above a correct 3-byte key if the
   English-frequency term dominates. The word-dictionary bonus is what
   separates real plaintext from printable junk — keep it weighty.

## Current solver confidence (empirical)

| Scenario                          | Outcome                                        |
|-----------------------------------|------------------------------------------------|
| Single-byte XOR                   | Exact, reliable.                               |
| Multi-byte XOR, short key (≤4)    | Recovered in tests (`k3y`, `testkey12`).       |
| Multi-byte XOR, 6-byte key        | Near-miss possible (`stcmrt` for `secret`);    |
|                                   | known-key mode is the exact fallback.          |
| Caesar / Atbash                   | Exact (Caesar ranked; inspect top rows).       |
| Vigenere, known key               | Exact.                                         |
| Vigenere, auto-break              | Heuristic; key-length guess via coincidence +  |
|                                   | per-column Caesar.                             |
| Encoding auto-detect              | Exact when clean; manuals available.           |

## Report pipeline

- `build_file_report`: metadata cards → metadata table → PE/ELF extras →
  entropy + per-block bar → strings (≤400 shown) → hex preview (≤200) →
  letter histogram → findings list.
- `build_solver_report`: generic candidate sections with key/score header
  and a truncated preview block. Keep `_preview` bounded (2048 chars)
  to keep reports small.

## Gotchas for the UI thread

- CustomTkinter widgets are NOT thread-safe. Never call `.insert/.delete`
  on a `ResultBox` from the worker thread; the `Worker` helper marshals
  results to `after()` on the main thread.
- Set a minimum window size (`964×620`) and cap hex-dump row counts to
  avoid freezing on huge files.
- `open_file()` disables nothing; heavy work happens in pages via
  `Worker` so the window stays responsive.
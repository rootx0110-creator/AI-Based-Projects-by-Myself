# Phishing Email Analyzer — Memory & Resource Document

> Describes memory usage, resource allocation, and performance characteristics.

## Execution Model

The application is a single Python process (GUI thread + one worker thread per
analysis). Memory is managed by CPython's reference counting + generational GC.

```
┌──────────────────────────────────────────────────────────────┐
│                        PROCESS                               │
│  ┌────────────┐   ┌────────────┐   ┌────────────────────┐   │
│  │ main thread │   │ UI objects │◄──│  worker thread     │   │
│  │ (tkinter    │   │ (widgets)  │   │  (email analysis)  │   │
│  │  event loop)│   │            │   │                    │   │
│  └────────────┘   └─────┬──────┘   └─────────┬──────────┘   │
│                         │                    │              │
│                         ▼                    ▼              │
│               ┌───────────────────────────────────┐         │
│               │      data/app_state.json (disk)   │         │
│               └───────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

## Memory Consumers

| Consumer                | Approx. size               | Notes                              |
| ----------------------- | -------------------------- | ---------------------------------- |
| Email raw source        | size of `.eml` file (up to ~20 MB declared cap) | Kept only while parsing |
| Parsed message object   | ~2× raw source              | Storage of MIME parts, decoded text |
| Header map              | small (~5–20 KB)            | Normalized headers, decoded values |
| URL results             | ~1 KB per URL               | Heuristic evidence lists            |
| Attachment hashes       | negligible (fixed strings)  | Feeds from chunked hashing          |
| HTML report (string)    | ~10–80 KB                   | Only built during export            |
| GUI widget tree         | stable (<10 MB)             | Grows only with new components      |

## Transient Spikes (Peak Memory)

| Operation                     | Peak ratio to raw size | Why                                   |
| ----------------------------- | ---------------------- | ------------------------------------- |
| Body decode (quoted-printable) | ~3× raw                | Interim byte buffers during MIME decode |
| HTML->text extraction (if used)| ~2× raw                | `HTMLParser` buffering                  |
| Report generation             | ~1.5× raw              | HTML string + template copies          |

## Streaming Hashing

Attachments are **not loaded wholly into memory**. SHA-256/MD5 hashes are computed
via a 1 MB rolling buffer:

```python
def compute_hashes(fileobj, chunk=1024 * 1024):
    sha256 = hashlib.sha256(); md5 = hashlib.md5()
    while block := fileobj.read(chunk):
        sha256.update(block); md5.update(block)
    return sha256.hexdigest(), md5.hexdigest()
```

This bounds the memory footprint of large attachments to `O(chunk)` regardless
of file size.

## Thread & Garbage Collection

- One non-daemonic worker thread per analysis; joined or dropped at completion.
- Long-lived strings (raw headers, decoded text) may be interned by CPython to
  reduce duplication; this is automatic and not tuned manually.
- No manual `gc.collect()` calls — CPython refcounting relains transient objects.

## Performance Budgets

| Metric                  | Target                     |
| ----------------------- | -------------------------- |
| Parse + analyze ≤ 2 MB eml | < 300 ms                |
| HTML report export      | < 200 ms (typical)         |
| Peak RAM                | < 150 MB (typical 60 MB)  |
| Startup                 | < 2 s on SSD               |

## Waivable Leaks / Known Notes

- History is retained as int/str tuples only (no email body), so history growth
  is bounded (~>KBs) even at `max_history=50`.
- Repeated pasting of huge emails grows the text buffer; the UI shows a size hint
  and warns above 20 MB.
- CustomTkinter renders offscreen; there are no known widget leaks when frames
  are destroyed and re-created.

## Disk Usage

| Path                    | Typical size | Purpose             |
| ----------------------- | ------------ | ------------------- |
| `data/app_state.json`   | < 5 KB       | theme + history     |
| `reports/*.html`        | 10–80 KB each| exported reports     |

## Scaling Limits

- **Input**: emails up to 20 MB parsed incrementally; beyond that a warning is
  displayed and parsing may take > 1 s.
- **URLs**: the engine can classify hundreds of URLs; each is independent and
  O(1) per URL.
- **Attachments**: hashing is I/O bound only and linear in file size.

## Recommendations

1. Prefer opening `.eml` rather than `.msg` — `.msg` fallback requires a
   separate parser (increases memory ~3×).
2. Export reports immediately after analysis if the session holds multiple
   large emails.
3. For batch triage of many emails, consider calling the `engine/` layer from a
   script without the GUI — memory remains proportional to a single email.
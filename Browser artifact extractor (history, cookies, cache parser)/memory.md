# Browser Artifact Extractor - Memory Management

## Memory Architecture

### Application Memory Model

The Browser Artifact Extractor uses an in-memory processing model to handle extracted browser artifacts efficiently.

```
┌─────────────────────────────────────────────┐
│              APPLICATION MEMORY              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         SESSION CACHE                │    │
│  │  - Extracted history entries         │    │
│  │  - Parsed cookies                    │    │
│  │  - Cache metadata                    │    │
│  │  - Browser detection results         │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         TEMPORARY STORAGE            │    │
│  │  - Copied SQLite databases           │    │
│  │  - Temporary cache files             │    │
│  │  - Export staging files              │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         OUTPUT BUFFER                │    │
│  │  - HTML report generation            │    │
│  │  - JSON/CSV export streams           │    │
│  └─────────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
```

## Memory Usage Estimates

| Artifact Type     | Records | Approx. Memory |
|-------------------|---------|----------------|
| Browser History   | 10K     | ~5 MB          |
| Browser History   | 100K    | ~50 MB         |
| Cookies           | 1K      | ~2 MB          |
| Cookies           | 10K     | ~15 MB         |
| Cache Index       | 50K     | ~30 MB         |
| Combined Typical  | Mixed   | ~100 MB        |

## Memory Optimization Strategies

### 1. Lazy Loading
- SQLite records are fetched in batches (paginated queries)
- UI renders incrementally as data becomes available
- Large result sets use virtual scrolling in the frontend

### 2. Temporary File Management
- Locked browser DBs are copied to `%TEMP%` before reading
- Copies are deleted immediately after parsing
- No persistent storage of sensitive data on disk

### 3. Streaming Exports
- HTML reports are generated in chunks to avoid large string concatenation
- CSV/JSON exports write directly to file streams
- Memory is freed as export progresses

### 4. Garbage Collection
- Python GC handles most cleanup automatically
- Explicit `del` statements for large parsed objects after export
- Flask session data cleared after each request cycle

## Memory Limits

- **Minimum**: 256 MB available RAM recommended
- **Typical**: 50-150 MB during extraction
- **Peak**: Up to 300 MB for very large browser histories (200K+ entries)
- **Export**: Streaming keeps export memory under 50 MB regardless of size

## Cleanup Procedures

1. **On extraction complete**: Previous results cleared before new extraction
2. **On application close**: All temporary files deleted
3. **On error**: Partial results cleaned up, temp DB copies removed
4. **On export complete**: Export buffer flushed and freed

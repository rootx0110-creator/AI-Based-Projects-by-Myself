# Browser Artifact Extractor - Application States

## State Machine

```
                    ┌──────────────┐
                    │   IDLE       │
                    │  (Startup)   │
                    └──────┬───────┘
                           │
                    User clicks "Detect Browsers"
                           │
                    ┌──────▼───────┐
                    │  DETECTING   │
                    │  Scanning    │
                    │  system      │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
       │  CHROME      │ │ FIREFOX │ │  EDGE   │  ...
       │  FOUND       │ │ FOUND   │ │ FOUND   │
       └──────┬───────┘ └──┬──────┘ └──┬──────┘
              └────────────┼────────────┘
                           │
                    User clicks "Extract"
                           │
                    ┌──────▼───────┐
                    │  EXTRACTING  │
                    │  Processing  │
                    │  artifacts   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  COMPLETE    │
                    │  Results     │
                    │  ready       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
       │  VIEW       │ │ SEARCH  │ │ EXPORT  │
       │  History    │ │ Filter  │ │ Report  │
       └─────────────┘ └─────────┘ └─────────┘
                           │
                    User clicks "New Extraction"
                           │
                    ┌──────▼───────┐
                    │   IDLE       │ ← (Reset state)
                    └──────────────┘
```

## Detailed State Descriptions

### IDLE
- **Entry**: Application startup / reset
- **Display**: Welcome screen with "Detect Browsers" button
- **Data**: No artifacts loaded
- **Memory**: Minimal (~10 MB)

### DETECTING
- **Entry**: User initiates browser detection
- **Display**: Loading spinner with progress animation
- **Actions**:
  - Scan `%LOCALAPPDATA%`, `%APPDATA%` for browser directories
  - Verify database files exist and are readable
  - Count available artifacts per browser
- **Duration**: 1-5 seconds typically
- **Memory**: ~20 MB

### BROWSER_FOUND (per browser)
- **Entry**: Detection complete for a browser
- **Display**: Browser card with icon, name, artifact counts
- **Data**: Profile paths, DB file paths, artifact counts
- **User can**: Select/deselect browsers for extraction

### EXTRACTING
- **Entry**: User initiates extraction
- **Display**: Progress bar with per-browser status
- **Actions**:
  - Copy locked databases to temp directory
  - Parse history SQLite tables
  - Parse cookies SQLite tables
  - Scan cache directories
  - Normalize timestamps and data
- **Duration**: 2-30 seconds depending on data volume
- **Memory**: 50-300 MB (scales with artifact count)

### COMPLETE
- **Entry**: All selected extractions finished
- **Display**: Summary dashboard with tabs
- **Data**: All artifacts loaded in memory
- **Tabs**: History | Cookies | Cache | Summary
- **Features**: Search, filter, sort, export

### ERROR
- **Entry**: Any failure during detection/extraction
- **Display**: Error message with details and retry option
- **Recovery**: User can retry or modify selection
- **Logging**: Error details written to console

## State Persistence

- Application state is **not persisted** between sessions
- Each launch starts fresh in IDLE state
- No configuration files are written to disk
- Browser detection is performed fresh each time

## Thread States

| Thread         | IDLE | DETECTING | EXTRACTING | COMPLETE |
|----------------|------|-----------|------------|----------|
| Main (Flask)   | Wait | Handle    | Handle     | Handle   |
| Detection      | -    | Running   | -          | -        |
| Extraction     | -    | -         | Running    | -        |
| Export         | -    | -         | Idle       | On-demand|

# Browser Artifact Extractor - Architecture

## Overview

Browser Artifact Extractor is a standalone desktop application that extracts, parses, and presents browser artifacts (history, cookies, cached data) from locally installed browsers on Windows systems.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Flask Web Server (localhost)                           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │  HTML/CSS/JS  │  │  Jinja2      │  │  REST API    │  ││
│  │  │  Templates    │  │  Templates   │  │  Endpoints   │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                      LOGIC LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   History     │  │   Cookies    │  │   Cache      │      │
│  │   Extractor   │  │   Extractor  │  │   Extractor  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐      │
│  │   Parsers    │  │   Parsers    │  │   Parsers    │      │
│  │  (SQLite)    │  │  (SQLite)    │  │  (Files)     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
├─────────┼────────────────┼──────────────────┼───────────────┤
│         │         DATA ACCESS LAYER         │               │
│  ┌──────┴───────────────┴──────────────────┴───────┐      │
│  │         Browser Path Resolver                     │      │
│  │  ┌─────────────┐  ┌──────────────┐              │      │
│  │  │  Chrome      │  │  Firefox      │              │      │
│  │  │  Edge        │  │  Brave        │              │      │
│  │  └─────────────┘  └──────────────┘              │      │
│  └─────────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                      SYSTEM LAYER                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  OS File System  │  SQLite DB Access  │  File I/O       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Browser Detection Module
- Auto-detects installed browsers (Chrome, Firefox, Edge, Brave, Opera)
- Resolves user profile paths dynamically
- Supports multi-profile extraction

### 2. History Extractor
- Reads SQLite `History` databases
- Extracts: URLs, titles, visit counts, timestamps, referrers
- Converts Chrome timestamps (microseconds since 1601-01-01) to human-readable

### 3. Cookie Extractor
- Reads SQLite `Cookies` databases
- Extracts: domain, name, value, path, expiry, secure flag, httpOnly
- Decrypts encrypted cookie values (DPAPI on Windows)

### 4. Cache Extractor
- Parses cache index files and cached content
- Extracts: URLs, file sizes, MIME types, timestamps
- Identifies cached files on disk

### 5. Web Presentation Layer
- Flask-based local web server
- Single-page application with tabbed navigation
- Real-time extraction progress
- Export to HTML/JSON/CSV
- Search and filter capabilities

## Data Flow

```
User Clicks "Extract" 
    → Browser Detection scans system
    → Profile paths resolved
    → SQLite databases opened (read-only)
    → Artifacts parsed and normalized
    → Results stored in memory
    → Rendered in web UI
    → User can export as HTML report
```

## Technology Stack

| Component       | Technology          |
|----------------|---------------------|
| Language        | Python 3.x         |
| Web Framework   | Flask               |
| DB Access       | sqlite3 (stdlib)    |
| Templating      | Jinja2              |
| Frontend        | HTML5, CSS3, JS     |
| Packaging       | PyInstaller         |
| Encryption      | ctypes (DPAPI)      |

## Security Considerations

- Read-only access to browser databases (no modifications)
- Temporary copies of locked DB files to avoid file locks
- No network transmission of extracted data
- Local-only web server (127.0.0.1 binding)

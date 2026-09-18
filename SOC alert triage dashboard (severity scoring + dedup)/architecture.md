# SOC Alert Triage Dashboard - Architecture Document

## 1. Overview

The SOC Alert Triage Dashboard is a client-side web application designed for
Security Operations Centers to efficiently manage, score, deduplicate, and
report on security alerts. The entire application runs in the browser with
no backend dependencies.

## 2. High-Level Architecture

```
+-------------------------------------------------------------+
|                    PRESENTATION LAYER                        |
|  +-------------------------------------------------------+  |
|  |  index.html - Dashboard Layout & Components            |  |
|  +-------------------------------------------------------+  |
|  |  css/style.css - Theme, Layout, Responsive Design      |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------------+
|                    APPLICATION LAYER                         |
|  +------------------+  +------------------+  +------------+  |
|  |   app.js         |  |  reports.js      |  | data.js    |  |
|  |   - UI Controller|  |  - HTML Builder  |  | - Engine   |  |
|  |   - Event Mgmt   |  |  - PDF/Export    |  | - Scoring  |  |
|  |   - State Mgmt   |  |  - Charts        |  | - Dedup    |  |
|  +------------------+  +------------------+  +------------+  |
+-------------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------------+
|                      DATA LAYER                              |
|  +-------------------------------------------------------+  |
|  |  In-Memory Alert Store (JavaScript Objects)            |  |
|  |  - Alert Collection                                    |  |
|  |  - Severity Scores                                     |  |
|  |  - Deduplication Hash Map                              |  |
|  |  - Filter State                                        |  |
|  |  - User Preferences (localStorage)                     |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

## 3. Component Architecture

### 3.1 Presentation Layer (index.html + style.css)

| Component            | Description                                      |
|----------------------|--------------------------------------------------|
| Header Bar           | App title, global search, export button          |
| Metrics Panel        | KPI cards (total, critical, dedup rate, etc.)    |
| Filter Sidebar       | Severity, source, time range, status filters     |
| Alert Table          | Sortable, paginated alert listing                |
| Alert Detail Panel   | Slide-out panel for alert inspection             |
| Severity Badge       | Color-coded severity indicators                 |
| Charts Section       | Severity distribution & timeline visualizations |

### 3.2 Application Layer

#### app.js - Main Controller
- Initializes the application
- Manages event listeners and user interactions
- Coordinates between UI, data, and report modules
- Handles state transitions (viewing, filtering, selecting)

#### data.js - Data Engine
- Alert data model and sample data generation
- **Severity Scoring Engine**: Assigns 1-10 scores based on:
  - Alert source credibility
  - Threat type classification
  - Asset criticality
  - Temporal factors (time of day, age)
  - Environmental context
- **Deduplication Engine**: Identifies and merges duplicate alerts using:
  - Source IP + Destination IP + Alert Type hash
  - Fuzzy matching for similar alerts
  - Time-window based grouping
- Query and filter operations

#### reports.js - Report Generator
- Builds comprehensive HTML reports
- Includes embedded CSS for standalone HTML files
- Generates charts using SVG/CSS
- Supports one-click download via Blob API

### 3.3 Data Layer

- **Alert Object Schema**:
  ```
  {
    id: string,
    timestamp: ISO datetime,
    source: string,
    severity: string,
    severityScore: number (1-10),
    title: string,
    description: string,
    sourceIP: string,
    destIP: string,
    category: string,
    status: string,
    isDuplicate: boolean,
    duplicateOf: string|null,
    dedupGroup: number|null,
    MITRE: string,
    recommendation: string
  }
  ```

## 4. Severity Scoring Algorithm

```
Final Score = (SourceWeight × 0.25) + (ThreatWeight × 0.30) + 
              (AssetWeight × 0.20) + (TemporalWeight × 0.15) +
              (ContextWeight × 0.10)

Score Mapping:
  9.0 - 10.0  →  CRITICAL
  7.0 - 8.9   →  HIGH
  4.0 - 6.9   →  MEDIUM
  2.0 - 3.9   →  LOW
  0.0 - 1.9   →  INFO
```

## 5. Deduplication Algorithm

```
1. Generate fingerprint = hash(sourceIP + destIP + alertType + category)
2. For each new alert:
   a. Check exact match in dedupHashMap
   b. If match found within time window (default: 60 min):
      - Mark as duplicate
      - Link to original alert
      - Increment duplicate counter on original
   c. If no exact match, perform fuzzy match:
      - Compare title similarity (Levenshtein distance)
      - Compare source/dest overlap
      - Threshold: >80% similarity = duplicate
3. Maintain dedup groups for related alerts
```

## 6. Data Flow

```
[Sample Data / User Input]
        |
        v
[Data Engine - Severity Scoring]
        |
        v
[Deduplication Engine]
        |
        v
[Filtered Alert Collection]
        |
        v
[UI Rendering - Table, Charts, Metrics]
        |
        v
[User Interaction - Filter, Select, Act]
        |
        v
[Report Generation - HTML Export]
```

## 7. Technology Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Structure    | HTML5                               |
| Styling      | CSS3 (Custom Properties, Grid, Flex)|
| Logic        | Vanilla JavaScript (ES6+)           |
| Charts       | SVG / CSS-based                     |
| Storage      | localStorage (preferences)          |
| Export       | Blob API + Download Trigger         |

## 8. Design Principles

- **Zero Dependencies**: No external libraries or frameworks
- **Offline Capable**: Works without internet connection
- **SOC-Optimized**: Dark theme, high contrast, reduced eye strain
- **Performance**: Virtual rendering for large alert sets
- **Accessibility**: ARIA labels, keyboard navigation support

## 9. Security Considerations

- All data processed client-side (no network calls)
- No sensitive data persisted to disk beyond localStorage
- CSP-compatible inline styles minimized
- XSS prevention through proper input sanitization

# SOC Alert Triage Dashboard - State Management Document

## 1. State Overview

The application maintains several layers of state to manage the dashboard
experience. All state is held in memory during the session, with optional
persistence to localStorage for user preferences.

## 2. State Architecture

```
+------------------------------------------+
|            GLOBAL STATE                   |
|  +------------------------------------+  |
|  | alerts: Alert[]                    |  |
|  | filteredAlerts: Alert[]            |  |
|  | dedupGroups: Map<groupID, Alert[]> |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | filters: FilterState               |  |
|  | selectedAlert: Alert | null        |  |
|  | currentPage: number                |  |
|  | pageSize: number                   |  |
|  | sortBy: string                     |  |
|  | sortDirection: 'asc' | 'desc'      |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | ui: UIState                        |  |
|  | - sidebarOpen: boolean             |  |
|  | - detailPanelOpen: boolean         |  |
|  | - activeView: string               |  |
|  | - theme: string                    |  |
|  +------------------------------------+  |
+------------------------------------------+
         |
         v
+------------------------------------------+
|        PERSISTENT STATE (localStorage)    |
|  - savedFilters: FilterPreset[]          |
|  - columnPreferences: ColumnConfig[]     |
|  - refreshInterval: number               |
|  - dashboardLayout: LayoutConfig         |
+------------------------------------------+
```

## 3. State Definitions

### 3.1 Alert State

```javascript
{
  // Master alert collection (immutable after load)
  alerts: Alert[],

  // Currently displayed alerts (after filters applied)
  filteredAlerts: Alert[],

  // Deduplication groups
  dedupGroups: {
    [groupID: number]: {
      alerts: Alert[],
      totalCount: number,
      representative: Alert,  // Highest severity in group
      mergedTimeline: Event[]
    }
  },

  // Aggregate metrics (computed)
  metrics: {
    totalAlerts: number,
    uniqueAlerts: number,
    duplicateCount: number,
    deduplicationRate: number,
    criticalCount: number,
    highCount: number,
    mediumCount: number,
    lowCount: number,
    infoCount: number,
    avgSeverityScore: number,
    alertsBySource: { [source: string]: number },
    alertsByCategory: { [category: string]: number },
    alertsOverTime: { [hour: string]: number }
  }
}
```

### 3.2 Filter State

```javascript
{
  filters: {
    severity: string[],       // ['Critical', 'High', 'Medium', 'Low', 'Info']
    sources: string[],        // ['Suricata', 'Splunk', 'CrowdStrike', ...]
    categories: string[],     // ['Network', 'Endpoint', 'Authentication', ...]
    statuses: string[],       // ['New', 'Investigating', 'Resolved', 'False Positive']
    timeRange: {
      start: Date | null,
      end: Date | null
    },
    searchText: string,
    showDuplicates: boolean,  // true = show all, false = hide duplicates
    minSeverityScore: number, // 0-10
    maxSeverityScore: number  // 0-10
  }
}
```

### 3.3 Pagination State

```javascript
{
  pagination: {
    currentPage: number,      // 1-indexed
    pageSize: number,         // Default: 25
    totalPages: number,
    totalItems: number
  }
}
```

### 3.4 Sort State

```javascript
{
  sort: {
    field: string,            // 'timestamp' | 'severity' | 'source' | 'title' | 'score'
    direction: 'asc' | 'desc'
  }
}
```

### 3.5 UI State

```javascript
{
  ui: {
    sidebarOpen: boolean,
    detailPanelOpen: boolean,
    activeView: 'dashboard' | 'alerts' | 'reports' | 'settings',
    selectedAlertIds: string[],
    isMultiSelect: boolean,
    chartType: 'pie' | 'bar' | 'line',
    tableColumns: ColumnConfig[],
    isLoading: boolean,
    notifications: Notification[]
  }
}
```

## 4. State Transitions

### 4.1 Alert Lifecycle States

```
    [New Alert Generated]
            |
            v
    +------------------+
    |   NEW            |   Initial state upon detection
    +------------------+
            |
            v (auto-assign or user action)
    +------------------+
    | INVESTIGATING    |   Analyst is reviewing
    +------------------+
            |
            +----> +-------------------+
            |      | RESOLVED          |   Confirmed threat, mitigated
            |      +-------------------+
            |
            +----> +-------------------+
            |      | FALSE POSITIVE    |   No threat identified
            |      +-------------------+
            |
            +----> +-------------------+
                   | DUPLICATE         |   Merged into parent alert
                   +-------------------+
```

### 4.2 User Interaction State Machine

```
[Dashboard View]
    |
    +-- (click alert row) --> [Alert Detail Panel Open]
    |                              |
    |                              +-- (change status) --> [Status Updated]
    |                              +-- (add note)      --> [Note Added]
    |                              +-- (close panel)   --> [Dashboard View]
    |
    +-- (click filter) --> [Filters Applied]
    |                          |
    |                          +-- (clear filters) --> [All Alerts Shown]
    |
    +-- (click export) --> [Report Generated]
    |                          |
    |                          +-- (download) --> [HTML File Saved]
    |
    +-- (click chart) --> [Drill-down View]
                               |
                               +-- (back) --> [Dashboard View]
```

## 5. State Updates

All state updates follow an immutable pattern:

```javascript
// Pattern: Create new state object rather than mutating
function updateFilters(newFilters) {
  state = {
    ...state,
    filters: { ...state.filters, ...newFilters }
  };
  applyFilters();
  renderDashboard();
}

// Pattern: Derived state is recomputed on changes
function applyFilters() {
  state.filteredAlerts = state.alerts.filter(applyFilterConditions);
  state.pagination.totalItems = state.filteredAlerts.length;
  state.pagination.totalPages = Math.ceil(
    state.pagination.totalItems / state.pagination.pageSize
  );
  state.pagination.currentPage = 1;
}
```

## 6. State Persistence

### 6.1 localStorage Schema

```json
{
  "socDash_prefs": {
    "filters": { "severity": ["Critical", "High"], "showDuplicates": false },
    "tableColumns": [
      { "field": "timestamp", "visible": true, "width": 160 },
      { "field": "severity", "visible": true, "width": 100 }
    ],
    "pageSize": 25,
    "theme": "dark",
    "refreshInterval": 30
  }
}
```

### 6.2 Persistence Rules

| State Category     | Persisted? | Reason                          |
|--------------------|------------|----------------------------------|
| Alert Data         | No         | Regenerated each session         |
| Filter Presets     | Yes        | User preference continuity       |
| Column Layout      | Yes        | UI customization                 |
| Theme              | Yes        | UX preference                    |
| Selected Alert     | No         | Session-specific                 |
| Pagination         | No         | Resets on filter change          |
| Sort Order         | Yes        | User preference                  |

## 7. Event Bus

State changes propagate through a simple event system:

```javascript
Events = {
  'alerts:loaded':       () => { /* Rebuild metrics, render table */ },
  'filters:changed':     () => { /* Apply filters, reset pagination */ },
  'alert:selected':      () => { /* Open detail panel */ },
  'alert:statusChanged': () => { /* Update badge, recalculate metrics */ },
  'dedup:completed':     () => { /* Update dedup metrics and groups */ },
  'report:generated':    () => { /* Trigger download */ },
  'sort:changed':        () => { /* Re-sort and re-render */ },
  'page:changed':        () => { /* Render new page of results */ }
}
```

# Active Directory Attack Path Visualizer - Architecture

## Overview

The AD Attack Path Visualizer is a web-based application designed to visualize Active Directory attack paths in a lab environment. It provides a BloodHound-style interface for analyzing and displaying potential attack vectors within an AD domain.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser (Client)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Frontend (HTML/CSS/JS)                  │   │
│  │  • Graph Visualization (vis.js)                     │   │
│  │  • Attack Path Display                              │   │
│  │  • Report Generation UI                             │   │
│  │  • Data Import/Export                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Flask Backend Server                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Core Modules                           │   │
│  │  • AD Data Parser (BloodHound JSON)                 │   │
│  │  • Attack Path Analyzer                             │   │
│  │  • Graph Algorithm Engine                           │   │
│  │  • Report Generator (HTML)                          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Data Layer                             │   │
│  │  • In-Memory Graph Store                            │   │
│  │  • Session Management                               │   │
│  │  • File System (Reports, Imports)                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System                              │
│  • /reports/        - Generated HTML reports                │
│  • /uploads/        - Imported BloodHound JSON files        │
│  • /templates/      - HTML templates                        │
│  • /static/         - CSS, JS, images                       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (Web UI)

| Component | Technology | Purpose |
|-----------|------------|---------|
| Graph Visualization | vis.js | Interactive network graph rendering |
| UI Framework | Custom CSS/HTML | Modern, responsive interface |
| Charts | Chart.js | Statistics and metrics display |
| Report Viewer | HTML5 | Display generated reports |

### 2. Backend (Flask Server)

| Module | Purpose |
|--------|---------|
| `app.py` | Main Flask application, routes, and API endpoints |
| `ad_analyzer.py` | AD data parsing and attack path analysis |
| `graph_engine.py` | Graph algorithms (BFS, DFS, shortest path) |
| `report_generator.py` | HTML report generation |

### 3. Data Model

#### Node Types (AD Objects)
- **User** - Domain user accounts
- **Computer** - Domain-joined computers
- **Group** - Security and distribution groups
- **OU** - Organizational Units
- **Domain** - Domain objects
- **GPO** - Group Policy Objects

#### Edge Types (Relationships)
- `MemberOf` - User/Group membership
- `AdminTo` - Administrative access
- `HasSession` - Active sessions
- `CanRDP` - RDP access
- `CanPSRemote` - PowerShell remoting
- `ExecuteDCOM` - DCOM execution
- `SQLAdmin` - SQL admin access
- `AllowedToDelegate` - Constrained delegation
- `AllowedToAct` - Resource-based constrained delegation
- `ForceChangePassword` - Password reset rights
- `AddKeyCredentialLink` - Shadow Credentials
- `WriteDACL` - Write DACL permissions
- `WriteOwner` - Write Owner permissions
- `GenericAll` - Full control
- `GenericWrite` - Generic write access
- `Owns` - Object ownership
- `ReadLAPSPassword` - LAPS password read
- `ReadGMSAPassword` - GMSA password read

### 4. Attack Path Analysis

The system identifies attack paths using graph traversal algorithms:

1. **Shortest Path** - Find shortest path between two nodes
2. **All Paths** - Enumerate all paths between source and target
3. **High-Value Targets** - Identify paths to Domain Admins, etc.
4. **Kill Chains** - Multi-stage attack sequences

### 5. Attack Categories

| Category | Description |
|----------|-------------|
| Credential Access | Kerberoasting, AS-REP Roasting, DCSync |
| Lateral Movement | Pass-the-Hash, Overpass-the-Hash, RDP |
| Privilege Escalation | DCSync, Golden Ticket, Silver Ticket |
| Persistence | Golden Ticket, Skeleton Key, AdminSDHolder |
| Reconnaissance | ACL enumeration, Group discovery |

## Data Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   BloodHound │───▶│   Upload &   │───▶│   Graph      │
│   JSON Data  │    │   Parse      │    │   Storage    │
└──────────────┘    └──────────────┘    └──────────────┘
                                              │
                                              ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   HTML       │◀───│   Report     │◀───│   Attack     │
│   Report     │    │   Generator  │    │   Analysis   │
└──────────────┘    └──────────────┘    └──────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | Get full graph data |
| `/api/attack-paths` | POST | Find attack paths |
| `/api/analyze` | POST | Analyze specific node |
| `/api/import` | POST | Import BloodHound JSON |
| `/api/report/generate` | POST | Generate HTML report |
| `/api/report/<id>` | GET | Download report |
| `/api/search` | GET | Search nodes |
| `/api/stats` | GET | Get statistics |

## Security Considerations

- This tool is designed for **lab environments only**
- No actual AD queries are performed
- Data is stored in-memory (non-persistent by default)
- No authentication required (local lab use)
- Reports are stored locally

## Deployment

### Local Development
```bash
pip install -r requirements.txt
python app.py
```

### Docker (Optional)
```bash
docker build -t ad-visualizer .
docker run -p 5000:5000 ad-visualizer
```

## Performance

- Graph visualization supports up to 10,000 nodes
- Attack path analysis completes in <1s for typical lab environments
- Reports generate in <5 seconds
- Memory usage: ~50MB baseline + data size

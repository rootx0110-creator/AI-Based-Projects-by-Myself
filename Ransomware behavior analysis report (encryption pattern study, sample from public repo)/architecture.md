# Ransomware Behavior Analysis Report - Architecture

## Project Overview

This project is a web-based cybersecurity analysis platform for studying ransomware behavior patterns, encryption techniques, and attack methodologies using samples from public IOC repositories (MalwareBazaar, VirusTotal).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HTML (index.html)                                   │  │
│  │  - Semantic structure with sections                  │  │
│  │  - Navigation & dashboard components                 │  │
│  │  - Modal & toast notification systems                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │  CSS (styles.css)      │  │  Chart.js via CDN          │ │
│  │  - Glassmorphism UI    │  │  - ATT&CK bar charts       │ │
│  │  - Aurora backgrounds  │  │  - Memory usage line charts│ │
│  │  - Matrix rain canvas  │  │  - Real-time updates       │ │
│  │  - Responsive design   │  └────────────────────────────┘ │
│  └────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      LOGIC LAYER                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  JavaScript (app.js)                                 │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐   │  │
│  │  │ Sample Data │ │ Chart Data   │ │ Report       │   │  │
│  │  │ Repository  │ │ Engine       │ │ Generator    │   │  │
│  │  └─────────────┘ └──────────────┘ └──────────────┘   │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐   │  │
│  │  │ Matrix Rain │ │ Scan Overlay │ │ Counter      │   │  │
│  │  │ Engine      │ │ Controller   │ │ Animations   │   │  │
│  │  └─────────────┘ └──────────────┘ └──────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| Main Interface | `index.html` | Application shell with all sections |
| Styling System | `styles.css` | Visual design, animations, responsive layout |
| Application Logic | `app.js` | Data handling, chart rendering, report generation |

### 2. Core Features

#### Matrix Rain Background
- Canvas-based animated falling characters background
- 40+ Japanese/Katakana and alphanumeric characters
- Configurable opacity and speed (40ms interval)

#### KPI Dashboard
- Four key performance indicators:
  - Threat Level: CRITICAL (9.5/10)
  - Ransomware Family: Conti v3.7
  - Current Stage: 7/12 (Encryption)
  - Detection Rate: 98.3%

#### Encryption Pattern Analysis
Four pattern cards with animated visualizations:
1. **Hybrid AES-RSA Encryption** - Crypto chain visualization
2. **File Header Overwrite** - Block-based marker injection
3. **Sparse File Encryption** - 4KB interval block selection
4. **Multi-threaded Parallel Processing** - Thread activity simulation

#### Behavioral Analysis
- ATT&CK Technique Distribution (radar/bar chart via Chart.js)
- Critical behaviors with severity scores:
  - Shadow Copy Deletion (95%)
  - Registry Persistence (82%)
  - Ransom Note Creation (100%)
  - WMI Event Subscription (68%)
  - Network Beaconing (74%)
  - Anti-Debug Techniques (88%)

#### Attack Timeline
9-stage kill-chain visualization with timestamps
Markers for executed stages, active stage animation

#### Sample Repository
8 ransomware samples with:
- SHA-256 hashes
- Family identification (Conti, REvil, LockBit, BlackCat, Ryuk, Darkside, WannaCry, Petya)
- File sizes, types, detection ratios

#### Report Generation
Three report types:
1. **Full Analysis** - Complete report with all sections
2. **Executive Summary** - High-level findings only
3. **Technical Deep-Dive** - Cryptographic and forensic details

Output: Downloadable HTML document with embedded styling

## Data Flow

```
Sample Repository → Analysis Engine → Chart Data → Visualization
         ↓                    ↓
    IOC Database        Key Findings → Report Generator → HTML Download
```

## Security Considerations

- All sample data is illustrative and sourced from public repositories (MalwareBazaar, VirusTotal)
- Application is client-side only - no data leaves the browser
- Report generation is local - no server communication
- For authorized security research purposes only

## Dependencies

- Chart.js v4.4.0 (CDN)
- Google Fonts: Orbitron, Inter, JetBrains Mono

## Browser Compatibility

- Chrome 80+
- Firefox 78+
- Safari 14+
- Edge 80+

## Deployment

Static file serving only (no build step required):
```
index.html
styles.css
app.js
```

Open `index.html` directly in browser or serve via any static file server.
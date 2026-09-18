=====================================================================
 CYBERFORGE - Ransomware Behavior Analysis Report Platform
=====================================================================
 VERSION: 2.4.1
 LICENSED FOR: Authorized security research purposes only
 DATE: 2026-09-17
=====================================================================

 DESCRIPTION
=====================================================================
A web-based cybersecurity analysis platform for studying ransomware
behavior patterns, encryption techniques, and attack methodologies.
Uses sample data from public IOC repositories (MalwareBazaar,
VirusTotal) for educational and threat intelligence purposes.

 FEATURES
=====================================================================
1. MATRIX RAIN BACKGROUND - Animated canvas-based falling character
   effects with Katakana and alphanumeric characters
2. KPI DASHBOARD - Real-time metrics: threat level, family,
   kill-chain stage, detection coverage
3. ENCRYPTION PATTERN ANALYSIS - Visual representations of:
   - Hybrid AES-RSA encryption
   - File header overwrite
   - Sparse file encryption
   - Multi-thread parallel processing
4. BEHAVIORAL ANALYSIS - ATT&CK technique charts and critical
   behavior severity indicators
5. ATTACK TIMELINE - 9-stage kill-chain with timestamped events
6. SAMPLE REPOSITORY - 8 curated ransomware samples with hashes,
   families, sizes, and detection metrics
7. REPORT GENERATION - Downloadable HTML reports in 3 formats:
   - Full Analysis Report
   - Executive Summary
   - Technical Deep-Dive
8. LIVE SCAN SIMULATION - Animated analysis sequence overlay

 TECHNICAL REQUIREMENTS
=====================================================================
- Modern web browser (Chrome 80+, Firefox 78+, Safari 14+, Edge 80+)
- No build process required
- Internet connection for CDN resources (Chart.js, Google Fonts)

 FILE STRUCTURE
=====================================================================
index.html          - Main application interface
styles.css          - Visual styling and animations
app.js              - Application logic and report generation
architecture.md     - System architecture documentation
state.md            - Current system operational state
memory.md           - Memory forensics analysis
todo.txt            - Development todos and roadmap
readme.txt          - This file

 RUNNING THE APPLICATION
=====================================================================
Option A - DESKTOP APP (recommended):
    Double-click CyberForge.exe in the dist\CyberForge-win32-x64
    folder. Opens in its own dedicated application window with
    the full UI, offline Chart.js, and custom app icon.

    A portable zip is also available:
    dist\CyberForge-Windows-x64.zip  (extract & run CyberForge.exe)

Option B - Direct open (web):
    Double-click index.html in your file explorer

Option C - Local server:
    python -m http.server 8000
    Then visit: http://localhost:8000

 DESKTOP APP (ELECTRON)
=====================================================================
    Requires:  Node.js 24+ (only for rebuild)
    Build cmd:  npm run build
    Output:     dist\CyberForge-win32-x64\CyberForge.exe

    Files:
      main.js       - Electron main process (window creation)
      package.json  - App metadata & build script

 REPORTS
=====================================================================
To generate a report:
1. Click "Download Report" button
2. Select report type
3. Click "Generate & Download HTML"
4. Report saves to your Downloads folder

Report sections include:
- Executive summary with threat metrics
- Critical findings and severities
- Encryption pattern analysis
- ATT&CK technique coverage matrix
- Sample repository analysis
- Indicators of compromise (IOC)
- Print-ready formatting

 SAMPLE DATA
=====================================================================
8 ransomware families analyzed:
- Conti (DLL) - 1.2 MB
- REvil (EXE) - 846 KB
- LockBit (EXE) - 2.4 MB
- BlackCat (DLL) - 1.8 MB
- Ryuk (MEM) - 640 KB
- Darkside (EXE) - 954 KB
- WannaCry (EXE) - 512 KB
- Petya (MBR) - 1.1 MB

All hashes are formatted SHA-256 identifiers from public IOC feed.

 TECHNICAL ARCHITECTURE
=====================================================================
Frontend: HTML5 + CSS3 + JavaScript (vanilla)
Charts: Chart.js v4.4.0 (CDN)
Fonts: Orbitron, Inter, JetBrains Mono (Google Fonts)
Effects: Canvas API, CSS3 animations, Glassmorphism, Aurora gradients

All processing is client-side. No data transmission occurs.
No server backend required.

 TROUBLESHOOTING
=====================================================================
Q: Charts not loading?
A: Check internet connectivity (Chart.js loaded from CDN)

Q: Report downloads blocked?
A: Allow downloads in browser settings

Q: Matrix rain too intense/dim?
A: Adjust opacity of #matrixCanvas in styles.css

 DISCLAIMER
=====================================================================
This tool is for authorized security research and educational
purposes only. All analysis is based on publicly available sample
data. Crypto keys and configurations shown are illustrative.
Do not use with live malware. Analyze samples in isolated,
contained environments only.

=====================================================================
 SUPPORT
=====================================================================
For questions, issues, or contributions, please report via the
repository issue tracker.

© 2026 CyberForge Security Intelligence
================================================================================
           ACTIVE DIRECTORY ATTACK PATH VISUALIZER - README
================================================================================

A BloodHound-style web application for visualizing Active Directory attack paths
in lab environments.

================================================================================
                              FEATURES
================================================================================

• Interactive graph visualization of AD objects and relationships
• Attack path analysis between any two nodes
• Multiple attack categories: Credential Access, Lateral Movement, etc.
• Real-time path finding with visual highlighting
• HTML report generation and download
• Import BloodHound JSON data
• Dark/Light theme support
• Responsive modern UI

================================================================================
                           SYSTEM REQUIREMENTS
================================================================================

• Python 3.8 or higher
• pip (Python package manager)
• Modern web browser (Chrome, Firefox, Edge, Safari)

================================================================================
                            INSTALLATION
================================================================================

1. Clone or download this repository

2. Navigate to the project directory:
   cd ad-attack-path-visualizer

3. Install Python dependencies:
   pip install -r requirements.txt

4. Run the application:
   python app.py

5. Open your browser and navigate to:
   http://localhost:5000

================================================================================
                            QUICK START
================================================================================

1. LAUNCH THE APP
   Run: python app.py
   Open: http://localhost:5000

2. LOAD DATA
   Option A: Use the built-in demo data
     - Click "Load Demo" button
     - Sample AD environment will be loaded

   Option B: Import BloodHound data
     - Export your BloodHound data as JSON
     - Click "Import" and select your JSON file
     - Data will be parsed and visualized

3. EXPLORE THE GRAPH
   - Drag nodes to reposition
   - Scroll to zoom in/out
   - Click nodes to see details
   - Use sidebar filters to show/hide node types

4. FIND ATTACK PATHS
   - Right-click a source node → "Set as Source"
   - Right-click a target node → "Set as Target"
   - Click "Find Paths" in the Analysis panel
   - View highlighted attack paths

5. GENERATE REPORTS
   - Click "Reports" in the sidebar
   - Configure report options
   - Click "Generate Report"
   - Download as HTML

================================================================================
                           DEMO DATA
================================================================================

The application includes a demo lab environment with:

• 15+ User accounts (including Domain Admins, Service Accounts)
• 10+ Computer objects (Servers, Workstations)
• 8+ Security Groups
• 5+ Organizational Units
• Multiple attack paths including:
  - Kerberoasting
  - ACL abuse chains
  - Delegation attacks
  - Lateral movement paths

================================================================================
                         BLOODHOUND IMPORT
================================================================================

Supported BloodHound JSON formats:

• Users.json
• Computers.json
• Groups.json
• GPOs.json
• OUs.json
• Domains.json

Import steps:
1. Collect BloodHound data using SharpHound or BloodHound CE
2. Export as JSON (Ingest tab → Export)
3. In this app, click "Import"
4. Select your JSON file(s)
5. Data will be parsed and visualized

================================================================================
                       ATTACK PATH ANALYSIS
================================================================================

The tool identifies attack paths using graph algorithms:

• BFS (Breadth-First Search) for shortest paths
• DFS (Depth-First Search) for all paths
• Dijkstra's algorithm for weighted paths

Attack categories detected:
• Credential Access
  - Kerberoasting
  - AS-REP Roasting
  - NTLM Relay

• Lateral Movement
  - Pass-the-Hash
  - Overpass-the-Hash
  - RDP Access
  - WMI Execution

• Privilege Escalation
  - DCSync
  - ACL Abuse
  - Delegation Attacks

• Persistence
  - Golden Ticket
  - AdminSDHolder
  - Skeleton Key

================================================================================
                          REPORT GENERATION
================================================================================

Generate comprehensive HTML reports containing:

• Executive Summary
• Attack Path Overview
• Detailed Path Descriptions
• Risk Assessment
• Recommendations
• Interactive Graph (embedded)

Report options:
• Include/exclude graph visualization
• Choose color scheme
• Select attack categories
• Custom report title

================================================================================
                          CONFIGURATION
================================================================================

Configuration file: config.json

{
  "host": "0.0.0.0",
  "port": 5000,
  "debug": false,
  "max_nodes": 50000,
  "max_edges": 500000,
  "report_dir": "./reports",
  "upload_dir": "./uploads"
}

================================================================================
                         TROUBLESHOOTING
================================================================================

Q: Application won't start
A: Ensure Python 3.8+ is installed and dependencies are installed
   Run: pip install -r requirements.txt

Q: Graph not loading
A: Check browser console for errors
   Ensure data is loaded (click "Load Demo" or import data)

Q: Report generation fails
A: Check that /reports directory exists and is writable
   Ensure sufficient disk space

Q: Slow performance with large datasets
A: Reduce visible nodes using filters
   Disable physics simulation
   Close other browser tabs

================================================================================
                          SECURITY NOTICE
================================================================================

This tool is designed for AUTHORIZED SECURITY TESTING in LAB ENVIRONMENTS ONLY.

• Do NOT use against production environments without authorization
• Do NOT use for unauthorized access to computer systems
• Users are responsible for complying with all applicable laws
• The authors are not responsible for misuse of this tool

================================================================================
                            CREDITS
================================================================================

Built with:
• Flask - Web framework
• vis.js - Graph visualization
• Chart.js - Statistics charts
• Font Awesome - Icons

Inspired by:
• BloodHound - AD attack path analysis
• SharpHound - AD data collection

================================================================================
                             LICENSE
================================================================================

MIT License - Free to use, modify, and distribute.

================================================================================
                              SUPPORT
================================================================================

For issues or questions:
1. Check the README and documentation
2. Review the architecture.md file
3. Check state.md for application state details
4. Review memory.md for performance information

================================================================================

================================================================================
 ThreatIntel Feed Aggregator - README
 IOC ingestion + auto-blocklist
================================================================================

WHAT IS IT?
-----------
A self-hosted web application that pulls Indicators of Compromise (IOCs) from
open-source threat-intelligence feeds, stores them in a local database, can
auto-generate firewall / DNS blocklists, and produces downloadable reports.

  - Web UI at:    http://127.0.0.1:5100
  - No accounts:  single-operator tool, run it locally.


--------------------------------------------------------------------------------
1. INSTALL & START
--------------------------------------------------------------------------------
Option A - Windows (simplest):
  1. Make sure Python 3.9+ is installed (https://www.python.org/downloads/).
  2. Double-click  start.bat
     It installs dependencies and starts the server in a console window.
     Keep that window open while you use the app.

Option B - Manual:
  Open a terminal in this folder, then:

    python -m pip install -r requirements.txt
    python app.py

  When you see:  Running on http://127.0.0.1:5100  -> the app is ready.

Then just open a browser and go to:  http://127.0.0.1:5100


--------------------------------------------------------------------------------
2. FIRST USE (2 minutes)
--------------------------------------------------------------------------------
  1. Dashboard -> click  "Ingest All Feeds"  (top right).
     This downloads the 10 pre-configured public feeds (Abuse.ch Feodo,
     Abuse.ch URLhaus, Blocklist.de, Emerging Threats, Tor Exit Nodes,
     Greensnow, Binary Defense, CI Army, OpenPhish, Darklist.de).
     First run can take 1-3 minutes.
  2. You now have IOCs. Check them:
     Indicators  page shows every extracted IP / domain / URL / hash,
     with confidence, severity, source feed, and last-seen time.
  3. Generate a blocklist:
     Blocklist -> choose min confidence (0.5 works) -> choose format ->
     click "Generate Blocklist" -> a file downloads automatically.
  4. Export a report:
     Reports -> choose CSV / JSON / TXT -> click "Generate" -> download.


--------------------------------------------------------------------------------
3. USING THE PAGES
--------------------------------------------------------------------------------
Dashboard
  - Top cards: total IOCs, blocklisted, active feeds, high severity.
  - "IOCs Ingested - Last 14 Days" chart: daily intake trend.
  - Feed Health: did each feed succeed on its last check?
  - Recent Ingestion: last runs, new vs total IOC counts.

Feeds
  - "+ Add Feed" - register your own source:
      Name: friendly label
      URL : feed endpoint  e.g. https://example.com/blocklist.txt
      Format: TXT / CSV / JSON (matches the feed content)
      IOC Types: what to keep (IP, DOMAIN, URL, HASH, or ALL)
      Reputation (0-1): lets you weight how much to trust this source
  - Per feed: "Ingest" (fetch now), "Edit", "Del", toggle auto/include.
  - "Auto/on" badges show whether the feed runs in batch ingests.

Indicators
  - Search box + filters (type, severity, blocklist state).
  - Pagination at the bottom.
  - "Block" / "Unblock" button on each row:
      Blocked IOCs are excluded from generated blocklists (manual override).
  - "CSV" button downloads the current filtered selection as a report.

Blocklist
  - Minimum confidence: only IOCs at/above this score are included.
  - Output format:
      pf / PF Sense  -> paste into PF or pfSense aliases
      iptables       -> firewall rule set
      hosts          -> hosts-file entries (0.0.0.0 <name>)
      BIND           -> null zones for DNS sinkholing
      plain list     -> simple de-duplicated text list
  - "Generate Blocklist" creates the file, starts the download, and logs
    it into the history table below (which can re-download / regenerate).
  - A "pf" blocklist is also auto-generated after every successful
    ingestion batch (can be disabled in Settings).

Reports
  - Pick format (CSV / JSON / TXT), optional type/severity/search filters.
  - "Generate" -> file is created under the reports/ folder and downloaded.
  - "Generated Files" table lists everything produced; download any time.

Settings
  - Minimum confidence: default blocklist threshold (0.5).
  - Auto-generate blocklist after ingestion: on/off.
  - IOC expiry (days): how long an IOC stays eligible for blocklists
    unless it is re-seen in a feed (default 90).


--------------------------------------------------------------------------------
4. TIPS
--------------------------------------------------------------------------------
 * Re-ingest regularly to keep blocklists fresh:
      Dashboard -> Ingest All Feeds  (or Ingest per feed on the Feeds page).
      Stale indicators (not re-seen within expiry days) are excluded.
 * Schedule ingestion (optional):
      Windows:  Task Scheduler -> trigger -> Program: python
                Args: app.py  (or POST http://127.0.0.1:5100/api/ingest-all)
      Linux  :  cron:  0 */6 * * * curl -X POST http://127.0.0.1:5100/api/ingest-all
      This keeps IOCs + the auto blocklist up to date automatically.
 * Trusted-sources weighting: set low reputation (0.3-0.5) for noisy lists,
   high reputation (0.9-1.0) for curated feeds like Abuse.ch.
 * Refresh blocklist thresholds: raise "minimum confidence" on the Blocklist
   page to produce shorter, higher-confidence artifacts.
 * Security: the server binds to 0.0.0.0. For single-user use, browse from
   localhost only; put a reverse proxy / SSO in front for shared teams.


--------------------------------------------------------------------------------
5. FILES & FORMATS
--------------------------------------------------------------------------------
  data/threatintel.db          SQLite database (IOCs, feeds, logs, settings)
  reports/blocklist_*.txt      generated firewall/DNS blocklist artifacts
  reports/threat_report_*.csv / .json / .txt     generated reports

  Understanding automations:
   - Ingestion pipeline: fetch feed -> parse (TXT/CSV/JSON) -> extract IOCs
     (regex) -> validate (private IPs / junk domains dropped) -> dedupe ->
     store, refresh last-seen, compute confidence, severity.
   - Confidence = feed reputation (given when adding the feed).
   - Severity: high >=0.85, medium >=0.6, low otherwise.


--------------------------------------------------------------------------------
6. TROUBLESHOOTING
--------------------------------------------------------------------------------
 * Page won't load:
      Confirm the console says "Running on http://127.0.0.1:5100".
      Check nothing else is using port 5100 (change in app.py / PORT env var).
 * Ingestion fails for a feed:
      The feed's Status column shows the error (offline source, format
      mismatch, too large). Try a different format (TXT vs CSV).
 * Blocklist file is empty / too short:
      Raise min confidence lower, or confirm IOCs exist (Indicators page),
      or check expiry days in Settings.
 * Port already in use / want another port:
      setx PORT 5200   then start again (Windows), or edit app.py.


--------------------------------------------------------------------------------
7. FURTHER READING
--------------------------------------------------------------------------------
  architecture.md   - system design, data model, API reference, extensibility
  state.md          - current operational state, settings catalog, gaps
  memory.md         - engineering notes, decisions, conventions for maintainers

It was built as a web app on purpose: feeds are remote HTTP sources, the API is
usable by other SOC tools, and it runs on any OS. A Windows EXE/Task build can be
produced from the same code (see architecture.md, section 9) if a native
distribution is required.

================================================================================
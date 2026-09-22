=======================================================================
 SubnetPlanner — Custom Subnet Calculator & VLSM Planner
 Version 1.0.0 — Windows, runs 100% locally
=======================================================================

WHAT IS THIS?
-------------
A desktop tool for network engineers, students and admins to solve IP
subnetting problems in seconds:

  1. SUBNET CALCULATOR
     Enter any IP address and a prefix (/0 .. /32) - or real subnet
     mask / hosts-per-subnet / number-of-subnets - and the app shows:

       * Network address          * Broadcast address
       * First / last usable IP   * Total and usable host counts
       * Subnet mask + wildcard   * IPv4 class (A/B/C) + borrow bits
       * Binary notation          * A color-coded 32-bit address map
       * A table of every subnet   derived from the chosen prefix

  2. VLSM PLANNER
     Give it a base network (e.g. 192.168.10.0/24) and a list of
     segments with required host counts. The app allocates variable-
     length subnets (largest demand first), showing for every segment:

       * Block size and prefix    * Network / first / last / broadcast
       * Subnet mask              * Address-space utilization
     Overflow (demand > capacity) is flagged immediately.

  3. REPORTS
     Export any calculation - or a combined subnet + VLSM document -
     as a polished, self-contained HTML file you can save, print or
     share. No internet required, ever.

-----------------------------------------------------------------------
QUICK START
-----------------------------------------------------------------------
  1. Double-click SubnetPlanner.exe (no install needed).
  2. Pick the tab you need.
  3. Fill the inputs, press CALCULATE (or ALLOCATE).
  4. On the Reports tab choose "Export HTML" (or "Export Combined").

-----------------------------------------------------------------------
USING THE SUBNET CALCULATOR
-----------------------------------------------------------------------
  * Type an IP (e.g. 192.168.1.35) and a prefix (e.g. 26) then press
    ENTER or click CALCULATE.
  * The four mode buttons (MASK / PREFIX / HOSTS / SUBNETS) define how
    you want to express the subnet - the other fields update
    automatically.
  * "List subnets" shows all subnets created by the prefix. For large
    subnets the on-screen table caps at 256 rows; the HTML report
    always contains the complete list.
  * The 32-bit map below the results color-codes network bits (blue)
    and host bits (green). Hover-free - just look at it.

-----------------------------------------------------------------------
USING THE VLSM PLANNER
-----------------------------------------------------------------------
  * Set the base network (e.g. 192.168.10.0) and prefix (e.g. 24).
  * Add segments with the + button; enter a name (e.g. "Floor 1 LAN")
    and the required usable hosts. Use Example Data to try it fast.
  * Click ALLOCATE. Results appear in the table; usage % is shown live.
  * Save/load your segment list as JSON (VLSM > General) so you can
    reuse planning scenarios.
  * If the total demand exceeds the base network, the planner warns
    you and still shows the deficit.

-----------------------------------------------------------------------
REPORTS
-----------------------------------------------------------------------
  Tab: Reports
  * Export HTML ......... save the last calculation as a standalone
                         HTML page (opens in your browser).
  * Export Combined ..... subnet results + VLSM plan in one document.
  * Open exported ....... re-open the most recent exported file.
  * To print: open in your browser and use its Print dialog
    (choose "Save as PDF" to get a PDF).

-----------------------------------------------------------------------
DATA & PRIVACY
-----------------------------------------------------------------------
  * The app is 100% offline - nothing is uploaded anywhere.
  * It remembers window size / last inputs in
    `%USERPROFILE%\.subnetplanner\settings.json`.
  * IP plans you export are plain text/HTML. Treat them as
    network-sensitive information: save reports to locations you
    control.

-----------------------------------------------------------------------
NOTES & RFC DETAILS
-----------------------------------------------------------------------
  * Usable hosts = 2^(32-prefix) - 2  for prefixes /1../30.
  * /31 = 2 usable hosts (RFC 3021 point-to-point links).
  * /32 = 1 usable host (single-host / loopback).
  * VLSM block size = smallest power of two >= (required hosts + 2),
    which guarantees at least the requested usable count.
  * Classful classes: A = /8 default, B = /16 default, C = /24 default.

-----------------------------------------------------------------------
TROUBLESHOOTING
-----------------------------------------------------------------------
  * Exe won't start / firewall prompt: it does not listen on any port -
    safe to allow; first launch is a bit slower (one-file unpacking).
  * Fonts "wrong" or huge/small: the app scales for High-DPI Windows;
    restart after changing display scaling.
  * Antivirus false positive on one-file executables: add an exclusion
    or rebuild per memory.md. The source builds are fully inspectable.

-----------------------------------------------------------------------
BUILDING FROM SOURCE (developers)
-----------------------------------------------------------------------
  Requirements: Python 3.14, PyInstaller 6.22+, Pillow (for icon).
  From the project folder:

      python main.py                            # run from source
      python -m unittest discover -s tests -v   # run tests
      python -m PyInstaller --noconfirm --clean --onefile --windowed ^
          --icon assets/app.ico --name SubnetPlanner main.py
      :: result: dist\SubnetPlanner.exe

-----------------------------------------------------------------------
PROJECT FILES
-----------------------------------------------------------------------
  readme.txt        this manual
  architecture.md   technical architecture
  state.md          current build state & status
  memory.md         developer notes & gotchas
  todo.txt          task checklist & backlog

(c) 2026 SubnetPlanner. MIT-style source license - use freely, keep
reports accurate and verify your production plans independently.
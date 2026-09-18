TIMELINE BUILDER - Filesystem & Log Artifact Timeline Tool
===========================================================

WHAT IT DOES
------------
Timeline Builder scans a folder on disk and produces a chronological
timeline of events by combining:

  1. FILESYSTEM METADATA
     - file / folder creation time
     - last modification time
     - last access time
     - file size

  2. LOG ARTIFACTS
     - .log, .txt, .jsonl timestamped lines are parsed for common
       timestamp formats (ISO 8601, "YYYY-MM-DD HH:MM:SS",
       "MM/DD/YYYY HH:MM:SS", "DD.MM.YYYY", RFC 2822 and epoch
       seconds / milliseconds / microseconds)
     - each timestamped log line becomes a "log" timeline event

The events are merged, deduplicated by time, and shown in a clean,
sortable, filterable table. The result can be exported as a
self-contained HTML report (with charts, search, sorting and page
navigation) or as a CSV file.

REQUIREMENTS
------------
- Python 3.10+ (built with Python 3.14.7)
- pip packages: customtkinter, pillow, pyinstaller (build only)

RUN FROM SOURCE
---------------
    python main.py                 # launches the GUI
    python main.py --cli <folder> [--out report.html] [--csv out.csv]
                                   # headless scan + report (no GUI)

BUILD THE EXE
-------------
    python -m PyInstaller --noconfirm --clean --onefile --windowed ^
        --name TimelineBuilder --icon app.ico main.py

    or simply run:  build.bat

The finished executable is "dist\TimelineBuilder.exe".

USING THE GUI
-------------
1. Click "Choose Folder" and select a root directory to analyse.
2. Click "Scan" (keep default filters, or pre-tick event types and a
   date range before scanning).
3. Browse the timeline table. Click a row to see full details.
4. Click "Export HTML Report" to download a standalone report file.
5. Click "Export CSV" to download the raw event list.

FILES
-----
main.py             entry point (GUI, or --cli mode)
timeline_core.py    filesystem + log scanning and timeline engine
timeline_report.py  self-contained HTML report generator
timeline_app.py     CustomTkinter GUI
architecture.md     design overview
state.md            current development state
memory.md           project log / decisions
todo.txt            remaining work
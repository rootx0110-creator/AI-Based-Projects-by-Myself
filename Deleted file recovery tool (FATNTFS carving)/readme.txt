============================================================
   DELETED FILE RECOVERY TOOL  -  FAT / NTFS & Raw Carving
   Version 2.1
============================================================

WHAT IT DOES
------------
A Windows desktop application that scans FAT12/16/32 and NTFS volumes
to find deleted files and recovers them back to your disk. It also
performs raw file carving - scanning the raw device for file signatures
- so it can find fragments even when the filesystem metadata is gone.

FEATURES
--------
- Clean, modern LIGHT theme interface
- Top tab bar with full-width tab buttons (Disks / Scan / Results /
  Recovery / Report)
- Drive explorer: logical volumes, physical disks, volume labels, sizes
- Automatic filesystem detection at boot sector
- FAT deleted-entry analysis & cluster-chain recovery
- NTFS $MFT mining with resident and non-resident (data-run) recovery
- Raw carving for ~50 file-signature families (JPG, PNG, PDF, DOC/XLS,
  ZIP/RAR, MP3/MP4/AVI, SQLite, EXE and many more)
- Three scan modes: Filesystem-only, Raw-carving-only, or both (Quick)
- Live progress bar + activity log during the scan
- Searchable / filterable results table
- Bulk recover with per-file progress (Select All / Clear)
- HTML report generation: summary cards, filesystem details, file-type
  breakdown chart and the complete file list
- Report "download" via Save As, or open straight in the browser
- Packaged as a single EXE (no Python install required)

QUICK START
-----------
1. Run  DeletedFileRecovery.exe
2. (Recommended) Right-click -> Run as administrator when opening,
   so the tool can access raw sectors for real recovery.
3. Disks tab -> pick the drive you want to analyse.
4. Scan tab -> choose a mode and click Start Scan.
5. Results tab -> search/inspect what was found.
6. Recovery tab -> tick files (or Select All), pick a destination,
   click Recover Selected.
7. Report tab -> Open in Browser or Save Report (.html).

Scan Modes
----------
- Filesystem (FAT/NTFS) : fast - reads directory tables / $MFT.
- Raw Carving only        : slower - scans the whole device for
                            signature-based files.
- Quick (FS + Raw)        : recommended - both passes.

RECOVERY QUALITY
----------------
A deleted file's data is only as good as the underlying disk state:
if the clusters have been overwritten since deletion, the recovered
file may be partial or unreadable. Stop using the disk immediately
after accidental deletion for the best results.

ADMINISTRATOR NOTE
------------------
Raw volume access needs Administrator privileges. Without elevation,
drive listing still works, but scanning will show an access error.
Right-click the EXE and choose "Run as administrator".

BUILDING FROM SOURCE
--------------------
Requirements: Python 3.10+ (tested on 3.14)

    pip install -r requirements.txt
    build.bat            (or: pyinstaller DeletedFileRecovery.spec)

Output: dist\DeletedFileRecovery.exe

TESTS
-----
    python tests\test_fat.py
    python tests\test_ntfs.py
    python tests\test_carver.py

DISCLAIMER
----------
Use only on disks you own or are authorised to recover. Recovered files
should be handled in accordance with applicable laws and policies.

============================================================
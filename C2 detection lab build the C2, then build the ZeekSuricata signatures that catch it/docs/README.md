# C2 Detection Lab

Build a C2, then build the Zeek / Suricata signatures that catch it —
all inside a loopback-only desktop lab that ships as a single .exe and
exports HTML reports.

## Files

- `docs/architecture.md` — system architecture
- `docs/state.md` — current state, limitations, backlog
- `docs/memory.md` — operational memory / conventions / gotchas
- `docs/RUN_INSTRUCTIONS.md` — how to run the app and the lab exercise

## Run

- **exe:** `dist\C2DetectionLab.exe` (no Python needed)
- **source:** `pip install -r requirements.txt; python main.py`

## Rebuild

```powershell
powershell -File build_exe.ps1
```

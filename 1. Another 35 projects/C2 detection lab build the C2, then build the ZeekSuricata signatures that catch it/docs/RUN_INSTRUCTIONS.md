# C2 Detection Lab — Application Run Instructions

> v1.0.0

## 1. Prerequisites

- **Packaged exe:** Windows 10/11 ×64. No Python required.
- **Run from source:** Python 3.14, then:
  ```powershell
  pip install -r requirements.txt
  python main.py
  ```

## 2. Quick start (the 5-minute lab)

1. Launch **C2DetectionLab.exe** (or `python main.py`).
2. **Lab Control** tab → pick a **Profile** (start with *Cobalt Strike Beacon*).
3. Set **Port**, **Interval**, **Jitter**, **Duration** → press **Start Lab**.
   Watch beacons appear in the live table as the agent checks in.
4. Press **Stop Lab** (or let the duration elapse).
5. **Lab Control** tab → **Run Detection** → findings populate the Dashboard.
6. **Reports** tab → **Download HTML (Full)** or **(Summary)** → report opens in
   your default browser and is saved to `outputs/`.

## 3. Workflow that teaches detection

1. Generate a session (step 2 above).
2. Read the **Generated Signatures** tab — Suricata rules, Zeek signatures, and
   the Zeek script `beacon_detect.zeek`.
3. Run Detection and audit the **Findings**: each is tagged with the rule/SID
   that produced it, so you can map *evidence → rule* like a real IR review.
4. Re-run with a different profile (e.g. *Generic HTTP Beacon*, low-and-slow)
   and compare verdicts. Note how a leaner fingerprint produces fewer CRITICAL
   content matches and leans on the behavioural layer.
5. Export the rules (`File ▸ Export ▸ Signatures…`) and try the deployment
   cheat-sheet in `memory.md`.

## 4. User interface reference

| Region      | What it does                                                        |
|-------------|----------------------------------------------------------------------|
| Menu bar    | File (New/Export/Exit), Report, Rules, Help (docs + About)           |
| Toolbar     | Start, Stop, Clear, Run Detection, Generate Report, Open in Browser  |
| Dashboard   | Stat cards: beacons, findings, alerts, verdict                        |
| Lab Control | Profile/config controls + live beacon table                          |
| Signatures  | Generated Suricata / Zeek / Zeek-script text per profile             |
| Reports     | HTML preview + download (Full/Summary), JSON log export              |
| Docs        | architecture.md, state.md, memory.md, run instructions               |
| Status bar  | Server state, beacon counter, last artifact written                  |

## 5. Report download options (HTML)

- **Reports ▸ Download HTML (Full)** — complete report: summary, metrics,
  timing model, all findings, full session log, full rule text, URI usage.
- **Reports ▸ Download HTML (Summary)** — executive summary, findings and rule
  overview — ideal for sharing.
- **Reports ▸ Open in Browser** — render a preview instantly without saving.
- **Reports ▸ Export JSON log** — raw beacon events for analysis elsewhere.

Files are written under `outputs/` by default (next to the exe when packaged).

## 6. File ▸ Export options

| Action                        | Writes                                     |
|-------------------------------|--------------------------------------------|
| Report ▸ HTML (Full)          | `outputs/reports/C2DetectLab_<ts>_full.html` |
| Report ▸ HTML (Summary)       | `outputs/reports/C2DetectLab_<ts>_summary.html` |
| Report ▸ JSON log             | `outputs/reports/C2DetectLab_<ts>.json`      |
| Rules ▸ Signatures…           | folder of `.rules`, `.sig`, `.zeek` files    |
| Help ▸ Export Documentation   | `docs/architecture.md`, `state.md`, `memory.md`, `README.md` |

## 7. Troubleshooting

| Symptom                              | Fix                                              |
|--------------------------------------|---------------------------------------------------|
| "port in use"                        | Pick another port in Lab Control, or quit the app using it. |
| No beacons appear                    | Confirm **Start Lab** began the *server list* in the status bar, then the *beacon agent*. |
| Report looks empty                   | A detection must be run *after* a session with ≥1 event. |
| Rule export folder empty             | Run a session + detection first so rules reflect the active profile. |
| exe blocked by antivirus             | `--onefile` pyinstaller builds are sometimes flagged; add an allow rule (lab tool). |
| Tk/legacy font rendering             | Restart app; the UI uses the platform-default theme (`vista` on Windows). |

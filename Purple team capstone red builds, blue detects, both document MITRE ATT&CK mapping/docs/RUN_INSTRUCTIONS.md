# Run instructions

## GUI mode (recommended)

1. Double-click `dist\PurpleTeamCapstone.exe` (or run `python main.py`).
2. **Dashboard** - check the techniques you want red to build, click
   *Build (Red)*, then *Detect (Blue)*.
3. **Red tab** - watch each technique's artifacts land in the lab target.
4. **Blue tab** - inspect findings and severities after the scan.
5. **MITRE tab** - study the technique × rule coverage matrix.
6. **Report tab** - *Download HTML report*, pick a location, then *Open report*.

## CLI / headless

```powershell
python main.py --cli            # full exercise, all techniques, HTML report
python main.py --cli T1053.005,T1041
python -m purpleteam.selftest   # engine self check, returns 0 on success
```

## Data locations

| Item | Path |
| --- | --- |
| Lab sandbox (red artifacts) | `outputs/lab_target/` |
| Last session (JSON) | `outputs/last_session.json` |
| Reports | `outputs/reports/*.html` |

When running the frozen EXE these land next to the executable (or in
`%LOCALAPPDATA%\PurpleTeamCapstone` if the exe folder is read-only).

## Troubleshooting

* **AV flags the EXE** - PyInstaller one-file apps are commonly flagged by
  heuristic AV. Use an allow-listed lab machine; build from source if needed.
* **Report download in the menu is disabled** - run at least one exercise so a
  downloadable session exists.
* **Ports blocked** - the exfiltration module binds an ephemeral loopback port
  only; firewall policy targeting 127.0.0.1 may still interfere.

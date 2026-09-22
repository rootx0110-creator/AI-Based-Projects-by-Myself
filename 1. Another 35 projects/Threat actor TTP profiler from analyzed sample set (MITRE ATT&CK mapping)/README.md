# Threat Actor TTP Profiler — MITRE ATT&CK Mapping

Desktop tool that analyzes a set of suspicious/malicious samples and produces a
**threat-actor TTP profile** mapped to MITRE ATT&CK. It inspects PE binaries and
text-based samples (scripts, module text), scores evidence by confidence, cross-ranks
those techniques against built-in threat-actor profiles, and exports a self-contained
**HTML report** you can save and share.

## Features

- **Multi-signal analysis** — PE imports & DLLs, embedded strings, string-based IOC
  extraction (URLs, IPs, domains, emails, registry paths), packer/entropy traits, and
  YARA hits (when `yara-python` is installed; a pseudo matcher otherwise).
- **MITRE ATT&CK mapping** — 70+ detection rules covering 70+ techniques/sub-techniques;
  techniques surface only when weighted evidence exceeds a confidence threshold, with
  each finding showing its exact evidence and confidence.
- **Threat actor ranking** — matches detected techniques against 14 built-in actor
  profiles (Turla, APT41, Kimsuky, Cobalt Group, Charming Kitten, Equation Group, …)
  using weighted overlap and coverage scores.
- **Sample-set workflows** — analyze a whole directory or individual files, re-analyze,
  and ingest prior analysis as JSON to skip re-extraction.
- **Self-contained HTML report** — KPIs, sample table, tactic-coverage bars, ATT&CK
  Navigator-style heatmap, per-technique evidence, IOC table, and actor ranking in one
  file with inline CSS/JS. Print-friendly and fully offline.
- **Dark CustomTkinter UI** — sidebar navigation with 7 pages: Dashboard, Samples,
  ATT&CK Mapper, Actor Profiles, Navigator, Reports, Settings.

## Quick start (source)

```powershell
pip install -r requirements.txt
python -m app.main
```

Headless engine self-test:

```powershell
python tools\selftest.py
```

## Building the EXE

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

Produces `dist\ThreatActorTTPProfiler.exe` (single-file, windowed, data embedded).

## Workflow

1. **Samples** page → *Add files / Add directory* to load a sample set.
2. Click **Run analysis** — the profiler extracts signals, maps techniques, and ranks actors.
3. Optional: tune the minimum-confidence slider under **Settings** and re-run.
4. **Reports** → *Preview / Save HTML* to save the standalone report, or *Export JSON* for ingestion later.

## Project layout

```
app/
  main.py            Entry point
  core/              Analysis engine (PE, strings, hashes, YARA, ATT&CK DB, actors, workbench)
  data/              Bundled knowledge base + YARA rules
    attack_techniques.json   ATT&CK technique metadata
    technique_rules.json     Detection rules (apis/dlls/strings/pe)
    actor_profiles.json      Threat actor profiles
    yara/samples.yar         Bundled sample rules
  reports/           HTML report generator
  ui/                CustomTkinter UI (theme, worker, main window, pages)
tools/selftest.py    Headless end-to-end check (engine + HTML report)
```

## Data schemas (JSON ingestion)

Reports can be exported as JSON and re-imported. Each sample supports:

```json
{
  "filename": "a.exe",
  "file_type": "pe",
  "md5": "...", "sha1": "...", "sha256": "...",
  "size_bytes": 123456,
  "imports": {"kernel32.dll": ["CreateRemoteThread"]},
  "strings": ["http://c2.example/panel.php"],
  "yara_rules": ["upx_packed"]
}
```

## Notes

- YARA is **optional**. Install `yara-python` for real rule matching; without it a
  lightweight pseudo matcher applies the bundled `samples.yar` rules.
- Confidence is on a 0–95 scale; strings alone can surface a technique once evidence
  is specific, but API/DLL/PE/YARA evidence dominates for binaries.
# Architecture

## Data flow

```
┌──────────────┐  selects techniques  ┌───────────────────────┐
│  GUI / CLI   │ ───────────────────► │   Exercise (session)   │
└──────────────┘                      │  exercise.py           │
                                      └───────────┬─────────────┘
                       red build                 │        blue detect
                                      ┌──────────▼──────────┐
                                      │   lab_target/        │
                                      │   outputs/lab_target │
                                      │   + sidecar index    │
                                      └──────────┬───────────┘
                                                 │
      .purpleteam_index.json  (artifacts) ───────┘
                                                 │ findings
                                      ┌──────────▼──────────┐
                                      │  score + coverage    │
                                      │  matrix (mitre.py)   │
                                      └──────────┬───────────┘
                                                 ▼
                                    report.py → HTML report (one file)
```

## Design decisions

1. **Single source of truth** - `mitre.py` holds both the technique library and
   the detection-rule library. `report.py`, `docs.py` and the GUI all render
   from it, so a technique added once appears everywhere.
2. **Artifact index** - red modules write files and also append JSON artifact
   records to `.purpleteam_index.json`. Blue rules scan that index
   (deterministic, fast), while the files remain on disk as evidence.
3. **Many-to-many mapping** - one rule (RULE-TOOL-DROP) surfaces T1105 and
   T1036.005; one technique (T1027) is surfaced by RULE-PS-OBFUSC. The coverage
   matrix shows the full relationship.
4. **Fidelity grades** - findings are tagged `high` (dedicated data source) or
   `low` (generic catch-all). The report separates *detection rate* from
   *dedicated coverage* so a catch-all can't mask weak signatures.
5. **Frozen-safe paths** - `config.py` picks the executable folder when running
   as a PyInstaller one-file build and falls back to LocalAppData when the
   exe folder is not writable. Reports/session/lab always land somewhere.

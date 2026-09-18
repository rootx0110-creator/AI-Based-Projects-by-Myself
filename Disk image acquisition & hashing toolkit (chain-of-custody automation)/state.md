# State — Disk Image Acquisition & Hashing Toolkit

> Auto-generated status file. Updated whenever project milestones change.

## Version

**v1.0.0** — initial release target.

## Build Status

| Milestone | Status |
|-----------|--------|
| Core models + JSON store | ✅ Done |
| Streaming hasher (MD5/SHA-1/SHA-256) | ✅ Done |
| Physical disk imaging (`dd` raw) | ✅ Done |
| Folder/image packaging acquisition | ✅ Done |
| Tamper-evident custody log | ✅ Done |
| HTML report generator | ✅ Done |
| CustomTkinter UI (6 views) | ✅ Done |
| PyInstaller EXE build | ✅ Done |
| Smoke test (window launch) | ✅ Done |
| Core logic tests (hash/chain/report) | ✅ Done |

## Current Focus

- Packaging the final EXE with PyInstaller.
- Verifying the built EXE launches and persists data next to itself.

## Known Limitations

1. Raw physical imaging requires **administrator** privileges on Windows.
2. No E01/S01 (Expert Witness Format) native writer — output is `dd`-style raw `.img`.
3. Folder acquisition produces STORE-mode (uncompressed) `.zip` images to preserve best-faith byte fidelity of logical evidence; byte-exact physical checksums are therefore computed on the packed archive itself.
4. GUI hash progress is updated via a background thread + UI `after()` polling.

## Next Steps

- [ ] Add E01 image writing (optional backend).
- [ ] Add scheduled/auto-verification ("re-verify before court").
- [ ] Add digital report signing (PGP) for non-repudiation.
- [ ] Localize UI (i18n).

## Runtime Data Layout

```
data/cases.json     # Cases + evidence registry (atomic JSON writes)
data/custody.json   # HMAC-chained custody log
data/images/        # Acquired images (.img / .zip)
data/reports/       # Generated HTML reports
```
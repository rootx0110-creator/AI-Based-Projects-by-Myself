# STATE.md — GLM Beacon Lab

Current state of the build. Update this file whenever you finish a work
session on the project.

## Status: ✅ WORKING — v1.0.0

Last verified: 2026-09-19 (engine self-test PASS, EXE built)

## What exists now

| Piece                       | State | Notes                                              |
|-----------------------------|-------|----------------------------------------------------|
| engine/crypto_tools.py      | ✅    | AES-128-CTR (FIPS-197 verified), HKDF, HMAC, hexdump |
| engine/certgen.py           | ✅    | pure-Python RSA-2048 + DER + self-signed cert, loads in `ssl` |
| engine/protocol.py          | ✅    | GLM1 frames, 6 message types, HKDF session keys    |
| engine/beacon.py            | ✅    | jittered check-in loop, canned commands only       |
| engine/listener.py          | ✅    | TLS server, event store, task queue, frame capture |
| engine/decrypt.py           | ✅    | MAC-first decryption, dictionary hint, evidence export |
| engine/report.py            | ✅    | self-contained dark HTML analyst report            |
| app.py                      | ✅    | Tkinter SOC console: live feed, beacons, tasking, Decryption Lab, report export |
| GLM_Beacon_Lab.spec         | ✅    | one-file windowed PyInstaller build                |
| dist/GLM_Beacon_Lab.exe     | ✅    | standalone build (see how_to_run.txt)              |
| ARCHITECTURE.md             | ✅    | component map + wire flow + crypto table           |
| MEMORY.md                   | ✅    | design decisions + gotchas                         |
| todo.txt                    | ✅    | prioritized backlog                                |

## Verified behaviour

- `python -m engine` → full headless loop prints **PASS**:
  TLS 1.3 tunnel → REGISTER → PING → TASK(whoami) → RESULT → capture →
  4 frames decrypted with correct passphrase, report written.
- Frames from a *second* session (different session nonce) correctly FAIL
  HMAC verification with the first session's nonce — the core blue-team lesson.
- EXE builds cleanly with zero third-party runtime dependencies.

## Known gaps / not yet built

- No real PCAP (libpcap) writer — capture is a text format for now.
- No JA3/JA4 fingerprint display (a nice future teaching widget).
- Beacon identity is fixed (`workstation-7/jdoe`); no multi-host fleet yet.
- No icon embedded in the EXE.

## Environment notes

- Python 3.14 at `C:\Python314\python.exe`; PyInstaller installed.
- Windows 11, bash shell (use POSIX syntax).
- Project dir contains `engine/certs/lab_*.pem` (auto-generated, self-signed,
  safe to delete — regenerated on next start).

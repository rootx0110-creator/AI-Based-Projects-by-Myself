# MEMORY.md — GLM Beacon Lab

Long-term notes for anyone (human or AI) resuming work on this project.

## What this project is

An **educational blue-team sandbox**: a simulated C2 channel that phones home
inside a TLS 1.3 tunnel, plus the full analyst workflow to decrypt the traffic
once the campaign key is "leaked". Shipped as a standalone Windows EXE with a
SOC-style dark console UI and HTML report export.

## Core design decisions (and why)

1. **Zero third-party runtime deps.** Pure Python stdlib: `tkinter` (GUI),
   `ssl` (transport), hand-rolled AES-CTR + HKDF + HMAC (`crypto_tools.py`),
   hand-rolled DER + RSA for the self-signed cert (`certgen.py`). This keeps
   the PyInstaller build small and bulletproof.
2. **Two-layer encryption on purpose.** TLS hides the traffic; the GLM1 frame
   layer (AES-CTR + truncated HMAC) gives the analysts something to peel.
3. **Flaws are features.** Nonce reuse, 4-byte MAC, hard-coded campaign key
   and a self-signed CA:TRUE cert are all deliberate teaching artifacts, each
   mapped to a detection idea in the report.
4. **MAC-first decryption.** The analyst workflow verifies the HMAC before
   trusting plaintext, so wrong passphrases fail loudly and safely.
5. **Simulation only.** The "implant" executes canned demo commands against
   fake host data (`workstation-7 / jdoe`). It never touches the real OS.

## Key facts

- Wire magic: `GLM1`; header = magic(4) + type(1) + len(4) + mac(4) = 13 bytes.
- Session keys: `HKDF-SHA256(passphrase, salt="glm-lab-salt",
  info="glm-beacon-lab/v1/session-keys", 48)` → 16-byte AES key + 32-byte MAC key.
- The 8-byte session nonce is announced by the beacon inside the tunnel
  before any framed message (models a smuggled ECDH session id).
- Check-in sequence: REGISTER → PONG ack → PING → (TASK → RESULT) → PONG bye.
- Listener stores raw frames in `pcap` and session nonces in
  `session_nonces` / `last_nonce` for the decryption exercise.
- AES core validated against FIPS-197 vector; `python -m engine` runs a full
  headless self-test (listener + beacon + decrypt + report) and prints PASS.

## Gotchas discovered during development

- TLS cert must use `basicConstraints` extnValue = `SEQUENCE{BOOLEAN TRUE}`
  (not double-wrapped) or OpenSSL rejects the chain.
- AES-128 needs 44 words / 11 round keys — off-by-two in the expansion loop
  breaks only the final round, which surfaces as garbage ciphertext.
- Do not share one fixed listener nonce across sessions: each session must
  use the beacon-announced nonce or every frame fails HMAC.
- Tk `Text.index("end-1c")` line counts are used to cap the live feed at 800
  lines; keep an eye on performance if you raise it.
- PyInstaller one-file + `console=False`: all diagnostics must go through the
  UI event feed, never print().

## Run / build quick reference

- Dev run: `python app.py`  (or `python -m engine` for headless self-test)
- Build:   `pyinstaller GLM_Beacon_Lab.spec --noconfirm` → `dist/GLM_Beacon_Lab.exe`
- Report:  generated in-app; standalone HTML, no external assets.

# GLM Beacon Lab — Architecture

**Encrypted C2 channel demo (TLS-wrapped beacon) + traffic decryption for blue-team study**

> Educational software for defenders. Every "implant" here is a simulation: it
> executes only canned demo commands against fake host data. Never point lab
> tooling at systems you do not own.

## 1. Mission

Give blue-teamers a safe sandbox to answer three questions:

1. What does a TLS-wrapped beacon actually look like on the wire?
2. How does an analyst peel the tunnel open once key material leaks?
3. Which design shortcuts (hard-coded keys, nonce reuse, truncated MACs,
   self-signed certs) turn an "invisible" channel into a detectable one?

## 2. Component map

```
┌───────────────────────────────  app.py (GUI)  ───────────────────────────────┐
│  SOC-style console                                                           │
│  ├── LIVE TRAFFIC feed          (event stream from listener)                 │
│  ├── CAMPAIGN controls          (port / key / sleep / jitter)                │
│  ├── REGISTERED BEACONS table   (host, user, pid, os)                        │
│  ├── TASKING bar                (queue whoami / ipconfig / dir …)            │
│  ├── DECRYPTION LAB             (frame list + plaintext + hexdump viewer)    │
│  └── REPORT EXPORT              (HTML / capture / plaintext downloads)       │
└──────────────┬───────────────────────────────┬───────────────────────────────┘
               │ threads                        │ reads
┌──────────────▼──────────────┐   ┌────────────▼─────────────────────────────┐
│  engine/listener.py         │   │  engine/report.py                        │
│  LabListener (TLS server)   │   │  self-contained HTML analyst report      │
│  • terminates TLS (lab.local│   │  • campaign metadata                     │
│  • reads GLM1 frames        │   │  • event timeline                        │
│  • decrypts + records       │   │  • decrypted message table               │
│  • event store + task queue │   │  • detection notes (MITRE-style)         │
└──────┬───────────────▲──────┘   └──────────────────────────────────────────┘
       │ accept         │ check-in loop
┌──────▼───────────────┴──────┐   ┌──────────────────────────────────────────┐
│  engine/beacon.py           │   │  engine/decrypt.py                       │
│  Beacon (simulated implant) │   │  analyst toolbox:                        │
│  • jittered sleep           │   │  • load_capture / derive_keys            │
│  • TLS connect (CERT_NONE!) │   │  • try_decrypt_frame (MAC-first)         │
│  • REGISTER→PING→TASK→RESULT│   │  • brute_force_hint (dictionary attack)  │
│  • canned command execution │   │  • save_recovered (evidence export)      │
└──────┬──────────────────────┘   └──────────────────────────────────────────┘
       │ protocol.encode_packet / frame_from_stream
┌──────▼───────────────────────────────────────────────────────────────────────┐
│  engine/protocol.py  — GLM1 wire format:                                     │
│  magic(4) | type(1) | ct_len(4) | hmac_prefix(4) | AES-CTR ciphertext        │
│  session keys = HKDF-SHA256(campaign passphrase)                             │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────┐   ┌───────────────────────────────────────┐
│  engine/crypto_tools.py         │   │  engine/certgen.py                    │
│  pure-Python AES-128 ("CBCS™"), │   │  self-signed cert via hand-rolled DER │
│  HKDF, HMAC, hexdump, XOR gate  │   │  + RSA-2048 keygen (no external deps) │
└─────────────────────────────────┘   └───────────────────────────────────────┘
```

## 3. Wire flow (one check-in)

```
 implant                                listener (tls://127.0.0.1:8443)
    │  TCP + TLS 1.3 handshake  ──────────▶  self-signed cert: CN=lab.local
    │  8B session nonce        ──────────▶  (models smuggled ECDH session id)
    │                                       ◀── "OK"
    │  GLM1 REGISTER (ciphertext) ────────▶  decrypt → host/user/pid/os
    │                            ◀────────  GLM1 PONG {"type":"ack"}
    │  GLM1 PING seq=N           ────────▶  decrypt → keepalive stats
    │                            ◀────────  GLM1 TASK "whoami"   (if queued)
    │  GLM1 RESULT "worksta..."  ────────▶  decrypt → operator output
    │                            ◀────────  GLM1 PONG {"type":"bye"}
    │  close                                  session recorded in capture
```

Every arrow above is one TLS-encrypted GLM1 frame. The listener records the
raw frame bytes, so the Decryption Lab can replay the exact byte streams.

## 4. Cryptographic design (deliberately flawed — that's the lesson)

| Layer        | Primitive                                   | Blue-team takeaway                        |
|--------------|---------------------------------------------|-------------------------------------------|
| Transport    | TLS 1.3 (self-signed `lab.local`)           | self-signed + CN quirks = TLS inventory flags |
| Frame crypto | AES-128-CTR ("CBCS™") pure-Python           | CTR without rotation = nonce reuse risk    |
| Integrity    | HMAC-SHA256, **truncated to 4 bytes**       | short tags are a false economy             |
| Key schedule | HKDF-SHA256(passphrase, "glm-lab-salt")     | hard-coded key material = single point of failure |
| Session id   | 8-byte nonce announced in-band              | one nonce per whole session → replay analysis |

`CBCS™` ("Counter-based Chained Block cipher") is the lab's teaching name for
its AES-CTR implementation so students never mistake it for a production
cipher. The AES core is validated against the FIPS-197 test vector in CI
(see `engine/__main__.py`).

## 5. Data flow for the analyst

1. **Capture** — `LabListener.pcap` stores every framed packet:
   `(timestamp, tag, direction, raw_bytes)`.
2. **Decrypt** — the Decryption Lab re-derives keys from the campaign
   passphrase (the "leaked keyfile" scenario), MAC-verifies each frame, then
   streams the recovered JSON into the viewer.
3. **Wrong key / second session** — frames whose session nonce differs fail
   HMAC verification; the tool shows exactly why (the MAC-first workflow).
4. **Report** — `engine/report.py` renders everything into one portable HTML
   file: timeline, decrypted messages, message mix, hexdumps and detection
   notes. No external assets, works offline, printable.

## 6. Threading model

| Thread            | Role                                            |
|-------------------|-------------------------------------------------|
| Tk mainloop       | UI, polls listener snapshot every 500 ms        |
| LabListener       | accept loop, spawns per-connection workers      |
| ClientConn (n)    | one TLS session lifecycle each                  |
| Beacon (n)        | jittered check-in loop per implant              |

Shared state is guarded: `events_lock` (event store), `task_lock` (task
queue). The UI never touches sockets directly — it consumes snapshots.

## 7. Deliberate limitations (education-first)

- Demo commands are canned strings; nothing touches the real OS.
- Fixed beacon identity (`workstation-7/jdoe`).
- One campaign key; no per-beacon keys (yet — see todo.txt).
- Traffic is loopback-only; port is configurable, hosts are not.

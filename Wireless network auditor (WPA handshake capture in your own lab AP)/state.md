# Wireless Network Auditor - State Management

**This document defines every application state, the allowed transitions, and
how the UI reflects it.**

---

## 1. Application-Level States

The app as a whole is in exactly one of these states:

| State | Meaning | Entry | Exit |
|-------|---------|-------|------|
| `IDLE`        | No capture running; ready for input    | App start / after stop / after report | `start capture` |
| `SCANNING`    | Network discovery in progress          | User clicks "Scan"                   | Scan completes → `IDLE` |
| `CAPTURING`   | A handshake capture is active          | `start capture`                      | `stop`, completion, or error |
| `DONE`        | Capture reached a terminal state       | Completion / abort                   | User clicks "New capture", resets to `IDLE` |

Global transition map:

```
         scan                     stop/completion
 IDLE ----------> SCANNING ---> IDLE <------------------+
   |                                                      |
   |  start capture                                       |
   v                                                      |
 CAPTURING --completion/abort--> DONE ---new capture-----> IDLE
   |
   +-- deauth burst (does not change state)
```

---

## 2. Capture State Machine (per-session)

Managed inside `capture/handshake.py` registry key `state`.

```
                 +-----------+
                 |   IDLE    |   waiting, nothing captured
                 +-----+-----+
                       |
                       | capture started
                       v
                 +-----------+
                 | LISTENING |   monitoring frames on channel
                 +-----+-----+   packets counter increments
                       |
                       | EAPOL message 1 observed (IEEE 802.1X Key)
                       v
                 +---------------+
                 | EAPOL_DETECTED|   at least one EAPOL frame seen
                 |  (>=1 msg)    |   packet map records msg types seen
                 +-------+-------+
                       |
                       | messages {1,2,3,4} all observed within window
                       v
                 +-------------------+
                 | HANDSHAKE_COMPLETE|   terminal success state
                 +-------------------+

  Any branch above can be interrupted:
        stop/abort  -->  returns to IDLE (session status = ABORTED)
   A half handshake (only msg 1-2 observed then silence)
                      --> stays in EAPOL_DETECTED until timeout
                          session status = PARTIAL
```

### Message tracking

`eapol_messages` is a count of distinct EAPOL message numbers observed
(frames with EtherType `0x888E`, 802.1X key descriptor). For a full
4-way handshake with a confident capture the expected values are:

| Messages observed | Meaning |
|-------------------|---------|
| 0                 | Not started |
| 1                 | AP sent ANonce (listening → detected) |
| 2                 | Client replied SNonce + MIC |
| 3                 | AP installs key |
| 4                 | Client acknowledges |
| ≥3 with msg 4     | Full handshake |

---

## 3. Persistent Records & their states

### sessions.status

| Value | Meaning |
|-------|---------|
| `COMPLETE` | Full 4-way handshake captured |
| `PARTIAL`  | ≥1 EAPOL frame but timed out before completion |
| `ABORTED`  | User stopped before completion |

### reports (created only from COMPLETE/PARTIAL sessions)

| Field | State |
|-------|-------|
| `score` | 0-100 security score computed by analyzer |
| `file_name` | The generated `.html` path on disk |

---

## 4. UI State Reflection

The capture page mirrors the backend registry at 1-second polling intervals
(`/api/capture/status`):

| Backend state | UI badge | UI controls |
|---------------|----------|-------------|
| `IDLE`            | gray "Idle" | Start Capture enabled |
| `LISTENING`       | blue "Listening" | Stop enabled; progress bar animated |
| `EAPOL_DETECTED`  | amber "EAPOL detected" | Stop enabled; "Trigger deauth" highlighted |
| `HANDSHAKE_COMPLETE` | green "Handshake complete" | "Generate report" button appears (confetti highlight) |
| capture finished  | - | "Download HTML report" link |

---

## 5. Persistence & Restart Behavior

- A running capture lives only in process memory.
- On app restart, in-flight captures are lost by design; the UI returns to `IDLE`.
- **Completed** sessions (COMPLETE/PARTIAL) are persisted in SQLite at the
  moment the terminal state is first polled by a request.
- Reports generated offline remain available as `.html` files in `reports/out/`
  and are re-indexed from disk on startup if they are missing from the table.

---

## 6. Error States

| Condition | Behavior |
|-----------|----------|
| Interface not found (live mode) | `/api/system` reports adapter as `unavailable`, UI shows red banner |
| Engine external tool missing | Capture fails fast, session stored as `ABORTED`, error bubbled to toast |
| DB write fails | Rolled back; `/api/capture/status` still returns registry data so UI can retry |
| Report generate fails | Partial HTML never registered; user sees error toast |

---

## 7. State Persistence Matrix Summary

| Item | In-memory | Flask session | SQLite | Disk |
|------|-----------|---------------|--------|------|
| Capture registry | ✅ | - | - | - |
| Scan cache | ✅ | - | - | - |
| Last target | - | ✅ | - | - |
| Networks ledger | - | - | ✅ | - |
| Sessions | - | - | ✅ | - |
| Reports index | - | - | ✅ | - |
| Report + .cap files | - | - | - | ✅ |
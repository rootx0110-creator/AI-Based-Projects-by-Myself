# State — Simulation State Machine

## Purpose

`state` is the transient, run-scoped execution state of the simulation. It
exists only while a training run is active and is destroyed on completion or
abort. Persistent data lives in `memory` (see memory.md).

## Lifecycle

```
IDLE ──start──▶ INTRO ──(ack)──▶ RUNNING ──complete──▶ REPORT ──(next)──▶ IDLE
  ▲                                │  ▲
  │                                │  (abort)
  └──────────────── aborted ───────┴───▶ REPORT (aborted outcome)
```

| Phase      | Meaning                                                        |
|------------|----------------------------------------------------------------|
| `IDLE`     | Menu/briefing screen; no run active                             |
| `INTRO`    | Mission brief overlay shown; world threaded but frozen          |
| `RUNNING`  | Player free to move; scenario clock, objectives and hazards live |
| `REPORT`   | Terminal; scoring locked, report generated, download armed      |

## Run state object

```json
{
  "runId": "RUN-0008",
  "phase": "RUNNING",
  "elapsedSec": 42.5,
  "player": { "x": 3.2, "z": -7.8, "health": 100, "ppeOn": true, "aim": { "yaw": 1.2, "pitch": 0.1 } },
  "objectives": {
    "order": ["don_ppe", "verify_alarm", "raise_alarm", "assess_spread", "isolate_fuel", "electrical_isolation", "extinguish", "evacuation", "incident_report"],
    "status": {
      "don_ppe": "done", "verify_alarm": "done", "raise_alarm": "active",
      "assess_spread": "locked", "isolate_fuel": "locked", "electrical_isolation": "locked",
      "extinguish": "locked", "evacuation": "locked", "incident_report": "locked"
    }
  },
  "decisions": [
    { "id": "d1_extinguisher", "choice": "co2", "correct": true, "t": 36.2 }
  ],
  "hazards": {
    "fireA": { "stage": "active", "growUntilSec": 90, "spreadChance": 0.03 },
    "smokeNorthCorridor": { "active": true }
  },
  "subsystems": { "fuelIsolated": false, "powerCut": false, "evacSignal": false, "alarmRaised": true },
  "events": [
    { "t": 4.1, "type": "action", "subtype": "don_ppe", "ok": true }
  ],
  "ticker": { "alarmAtSec": 4.1, "injuries": 0 }
}
```

## Timing & determinism

- A single `clock` advances `elapsedSec` each frame with a capped delta
  (max 50 ms) so a tab-throttled frame cannot corrupt the run.
- Fire growth and smoke spread are driven by `elapsedSec` only (no wall-clock
  math) so replays are reproducible.
- All increments to `events` are ordered by `t`.

## Rules applied while RUNNING

1. Objectives unlock strictly in the order of `objectives.order`. A locked
   objective shows as "next step" on the HUD but cannot be scored early.
2. Health damage only from: entering the active fire hazard zone (no PPE →
   −8/s, PPE → −2/s), and from choosing an incorrect suppression agent near an
   energized rack (electrical flash).
3. `aux flag`: any new hazard appearing (smoke, second fire) is appended to
   `hazards` by the scenario tick.

## Phase transitions

| Transition | Trigger                              | Side effect                                  |
|------------|--------------------------------------|----------------------------------------------|
| IDLE→INTRO | Trainee clicks Start Training         | Picks new `runId`, builds fresh run state    |
| INTRO→RUNNING | Trainee clicks I understand / countdown ends | Player spawns, alarm timer starts  |
| RUNNING→REPORT | All objectives done OR fatal injury OR trainee submits | Score locked, events frozen, report rendered |
| REPORT→IDLE | Trainee clicks New Session            | Run state nulled, memory updated             |

## Failure/convergence guarantees

- The status map never contains an objective with unknown key.
- At most one objective is `active` at a time.
- `hazards` and `events` are append-only during RUNNING to keep replay
  integrity.
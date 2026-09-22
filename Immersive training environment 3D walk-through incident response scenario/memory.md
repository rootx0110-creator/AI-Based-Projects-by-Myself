# Memory — Persistent Trainee Memory

## Purpose

`memory` is the part of the application that survives between runs and
sessions. It stores the trainee identity, attempt history, personal-best
metrics and the skill profile. It does **not** store anything about a run that
is still in progress (that is `state`, see `state.md`).

## Storage

- Primary: browser `localStorage`
  - key: `irtrn.memory`
- Fallback: a JSON file `memory_snapshot.json` exported by the trainee (via
  the memory panel in the UI) so the profile can be moved between machines.

## JSON schema

```json
{
  "schemaVersion": 1,
  "trainee": {
    "name": "Jane Operative",
    "callsign": "RESPONDER-01",
    "branch": "Site Security",
    "seal": 0,
    "skillProfile": { "safety": 0, "speed": 0, "accuracy": 0, "coverage": 0 }
  },
  "attempts": [
    {
      "id": "RUN-0007",
      "completedAt": "2026-09-20T14:02:11.000Z",
      "outcome": "protected",           // "protected" | "contained" | "failed" | "aborted"
      "score": 88,
      "grade": "A",
      "timeSec": 312,
      "checklist": { "done": 9, "total": 9 },
      "decisions": { "total": 5, "correct": 4 },
      "pillars": { "safety": 92, "speed": 81, "accuracy": 87, "coverage": 90 },
      "incidents": { "injuries": 0, "missedSteps": 1 }
    }
  ],
  "metrics": {
    "attemptsTotal": 7,
    "attemptsCompleted": 7,
    "bestScore": 91,
    "bestTimeSec": 268,
    "avgScore": 83
  }
}
```

## Meaning of fields

| Field | Meaning |
|-------|---------|
| `trainee.seal` | Earned rating badge 1 = Novice, 2 = Responder, 3 = Operator, 4 = Commander |
| `skillProfile` | Rolling weighted average per pillar (0-100), used for the radar chart |
| `attempts[]` | One entry per completed run (most recent last) |
| `metrics` | Derived roll-ups shown on the profile screen |

## Grading

| Grade | Score |
|-------|-------|
| A | ≥ 85 |
| B | 70-84 |
| C | 55-69 |
| D | 40-54 |
| F | < 40 |

Seal progression: 4 completed runs → Responder; 8 → Operator; 15 → Commander
(quality-weighted: >75% of runs must be grade B or better).

## Usage rules (for maintainers)

1. Read memory once at boot (`Memory.load()`).
2. Write memory only as whole snapshots (`Memory.save()`), never field-level,
   to keep the ledger consistent.
3. A run's results are folded into memory only when the run reaches a terminal
   state — never on abort during training walkthrough.
4. If the schema version changes, add a migration function in `Memory.migrate`
   instead of silently dropping old data.
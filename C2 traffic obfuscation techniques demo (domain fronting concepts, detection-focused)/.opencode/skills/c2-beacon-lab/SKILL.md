---
name: c2-beacon-lab
description: Run and interpret beacon jitter/regularity simulations for the C2 Traffic Obfuscation Lab. Use when generating beacon schedules, computing coefficient-of-variation verdicts, or teaching how beacon regularity supports C2 detection.
---

# C2 Beacon Lab

Simulate beacon check-in schedules and interpret their regularity the way a
detection engineer would.

## When to use
- Generating synthetic beacon schedules (interval + jitter)
- Evaluating whether a schedule looks like a fixed-interval C2 beacon
- Preparing the Beacon section of an HTML report for this lab

## Workflow

1. Create a schedule and compute stats:

```python
from c2obfuscator.core import BeaconSchedule, BeaconSimulator

sched = BeaconSchedule(interval=60, jitter_pct=15, count=20, seed=42)
stats = sched.stats()          # dict: mean, std, CoV, min, max
times = sched.generate()
verdict = BeaconSimulator().verdict(stats)
```

2. Interpret the verdict thresholds used by the lab:

| CoV (std/mean) | Severity | Meaning |
|---|---|---|
| < 0.05 | HIGH | Mechanically regular, fixed-interval beacon |
| < 0.25 | MEDIUM | Mostly regular; worth deeper review |
| < 0.60 | LOW | Jittered / human-affected |
| else | INFO | Not clearly beacon-like |

3. Document the rationale: state CoV, the severity, and WHY
   (e.g. "CoV=0.085 - mostly regular rhythm with 15% jitter").

## Output format
Return a short table of the requested config plus a one-line verdict. If the
user asked for a report, hand the results to the `html-report-generator` skill.
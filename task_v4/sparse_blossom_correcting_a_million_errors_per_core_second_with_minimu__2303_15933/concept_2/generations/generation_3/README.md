# Concept 2 — final planned generation 3

Mode B counterexample/falsification. This is the second ratchet and final planned
tournament generation for this concept: initial generation plus two ratchets.
It extends calibration directions, not numerical targets or perturbation size.

Expose **only `participant/`** to each fresh one-hour attempt. Never expose
`evaluator/`, `adversary/`, another attempt, parent concepts, or private reports.
Main owns champion selection, attempt orchestration, and subsequent status updates.
No fresh runner is launched by this builder.

The baseline is the actual generation-two champion v1. The new anisotropic
position-dependent directions have independently confirmed real failures.
Feasibility is **open / unknown**; no valid generation-three witness is known.
Do not interpret this as a proof of impossibility or as validated model difficulty.

```
/usr/bin/python3 -B evaluator/evaluate.py /path/to/witness.json --output result.json --summary-only
```

The trusted evaluator compiles once from `evaluator/hidden/full_state.cpp` if a
new binary is required; see `evaluator/README.md`. It never executes participant
code and has no internal wall watchdog. `status.json` and the frozen manifest
record the pre-launch audit, targets, domain, and exact baseline evidence.

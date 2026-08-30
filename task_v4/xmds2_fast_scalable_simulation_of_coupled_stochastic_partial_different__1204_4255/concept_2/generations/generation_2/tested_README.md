# Concept 2: robust nonlinear false convergence

Status: `pending_tournament`. Expose only `participant/` to tested agents. Keep evaluator, privileged probes, and baseline evaluation artifacts private.

From this directory:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
/usr/bin/python3 -B adversary/test_controls.py
```

Development budget: one hour of single-CPU work. The evaluator accepts a data-only JSON witness, never participant code. It uses frozen kernel copies in an isolated Python subprocess with 110-second wall, 100-second CPU, and 1536-MiB address-space limits. Its stdout is one objective JSON; `--output` optionally saves the same JSON.

Exact success target: **all five family members**, at **each of three late times**, must show a conservative low-band density gap **≥0.30** while the maximum eight-time complex-field coarse/fine difference is **≤1e-4**, sampled tail mass **≤0.02**, mass drift **≤2e-5**, and energy drift **≤2e-4**. Every reference must pass the independent/refinement checks. Full definitions are in `participant/input/protocol.json`.

Source connections and rationale are in `provenance.md`. Numerical evidence is in `adversary/` and `attempts/`. There is no declared tournament champion.

# c04 ratchet1: ready for one fresh agent

Only `participant/` is released to the agent. It contains TASK.md, input/ and
workspace/solver.py (a two-line unimplemented starter). The agent writes the root
`attempt/solver.py`. The attempt directory is empty at freeze; no fresh agent was
launched in preparation. Original pilot and probe artifacts are untouched.

There are six screening cases (two per family) and three reserved confirmation
cases (one per family), dimension 64 throughout, with endpoints 9000--20000.
There is no extra challenge split. The one public T=8500 example is unlabeled and
uses another seed. All equations, conventions and tolerances are public in
`participant/input/protocol.md`; source/method discussion remains author-only.

## Measured isolated validation

| Implementation | Split | Mean core | Worst family | Aggregate score | Worker seconds/case |
| --- | --- | ---: | ---: | ---: | ---: |
| Reference | Screening | 1.000000 | 1.000000 | 1.000000 | 1.105--3.581 |
| Reference | Confirmation | 1.000000 | 1.000000 | 1.000000 | 0.991--2.002 |
| Fixed weak | Screening | 0.629680 | 0.575000 | 0.613276 | 1.184--3.261 |
| Fixed weak | Confirmation | 0.643503 | 0.500000 | 0.600452 | 0.902--2.419 |

All 18 actual isolated executions succeeded. Every reference case and component
scores 1.0; reference peak RSS is 90,860 KiB. Parent wall time, including namespace
startup, reached 23.651 seconds for reference and 24.677 seconds for weak. The
runner uses strict worker wall 60 seconds, CPU soft/hard 61/62 seconds, 6 GiB,
one BLAS thread, and 30 seconds of startup grace (parent watchdog 90 seconds).
Full required summary fields and per-case CPU/wall/RSS evidence are in
`private/validation/{reference,weak}_{screening,confirmation}.json`.

## Reproduce evaluation

From the ALE root:

```bash
R=tasks_v3/reliability_of_lattice_gauge_theories__2001_00024/pilots/c04_colored_noise/ratchet1
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python "$R/private/evaluator.py" --submission "$R/private/reference" \
  --participant "$R/participant" --split screening --output /tmp/c04_ratchet1_reference_screening.json
```

Use `private/weak_baseline` for the weak implementation, `attempt` for the fresh
submission, and `--split confirmation` only for the reserved check. The evaluator
resolves the actual task root and imports only its common `isolated_eval` runner;
it never imports a submission into the evaluator process. No shared helper was
modified. NumPy 1.21.5 and SciPy 1.8.0 were used; no extra package is required.

`private/reference/precompute.py` is the author-only regeneration script, not a
participant dependency. Do not regenerate labels after the frozen attempt starts.
Exact cases, actual weak errors/anchors, outputs, residuals and final hashes are
under `private/challenge_pool`, `private/reference/outputs`,
`private/validation/scientific_checks.json` and `private/freeze.json`.

## Validity and stopping rule

`PROVENANCE.md` discloses the author reimplementation, effective secular model,
finite-cluster numerical correction and sampled-time objective. The closed-system
fidelity at the final time ranges from 0.117 to 0.635, so the cases do not merely
test a steady state. Winning actions include flat-high, flat-low and graded-high.
Weak decisions are often already correct; bath and independent audit errors still
matter. The weak anchor is the documented stronger white/local secular surrogate,
not the old nonsecular baseline; formulas, weights and floors remain unchanged.

A specialist block solver can potentially solve every case. If the second fresh
agent solves screening and confirmation, reject c04 rather than tighten again.

# Robust cat-state control on a heavy-hex plaquette

Design one open-loop pulse sequence that prepares
`GHZ+ = (|000000000000> + |111111111111>)/sqrt(2)` from `|+>^12`,
despite static calibration uncertainty. Submit a **control witness**, not a
simulator, fit, proof, or claimed fidelity.

The device is a 12-cycle (one isolated heavy-hex plaquette). Use exactly
24 alternating bond-matching layers with fixed nominal `exp(+i*pi*ZZ/4)`
gates, each followed by two-group `Rx` kicks. Only the 48 kick angles are
programmable; each must lie in `[-pi, pi]`. This explicitly generalizes the
all-bond/global-kick protocol of arXiv:2306.14887; see `input/protocol.md`
for the schedule, symmetry rationale, and precise uncertainty model.

## Assets and interface

- `input/problem.json`: graph, groups, bounds, target, and calibration ranges.
- `input/protocol.md`: exact mathematical contract and scoring rules.
- `input/training_scenarios.json`: 15 public examples, not the full test set.
- `workspace/simulator.py`: exact complex128 forward simulation and fidelity.
- `baseline/run_baseline.py`: runnable, deliberately nominal-only weak baseline.
- `baseline/pulses.json`: precomputed weak baseline and optional warm start.

From the participant directory:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python baseline/run_baseline.py --output submission
python workspace/score_public.py --submission submission
```

Submit a directory containing `pulses.json`, with exactly
`{"schema_version": 1, "angles": [[a0,b0], ..., [a23,b23]]}`. Angles are radians.
No adaptive controls, extra gates, measurements, postselection, adjustable ZZ
strengths, or scenario-specific sequences are permitted.

## Objective and resources

Pass iff the exact GHZ fidelity is **at least 0.95 in every frozen test
scenario** and the artifact is valid. The score is the minimum fidelity,
not the mean. Tests include nominal/axis/corner calibrations, structured
boundary stress, and held-out local bond disorder. The public family/ranges
are binding; passing is a finite-suite test, not a certificate for the continuum.

Use Python/NumPy/SciPy or other installed local tools; no GPU, network, or
external data are needed. Keep searches to at most four CPU threads and
about 2 GiB of working memory. Exact checking uses only 4096 amplitudes per
scenario. The trusted harness runs
`python evaluator/evaluate.py --submission DIRECTORY --output JSONPATH`;
the evaluator and its private assets are not participant inputs.

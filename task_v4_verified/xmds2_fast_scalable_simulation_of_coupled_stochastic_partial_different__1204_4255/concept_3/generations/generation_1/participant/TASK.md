# Coherent nonlinear matter-wave splitter

Construct one open-loop, smooth six-channel control waveform that transports a
two-component condensate and coherently splits it into two output ports in eight
dimensionless time units. The same waveform must work across the public joint
uncertainty envelope, including interaction strengths, trap frequencies, RF gain,
and differential detuning. Matching output densities alone is not enough: the
relative phase and the complete two-dimensional complex field matter.

**Assets.** `input/SPEC.md` is the full mathematical and artifact specification;
`input/protocol.json` gives machine-readable constants and bounds;
`input/public_cases.json` gives five development cases. `workspace/field_control.py`
provides a runnable NumPy/SciPy tensor-grid simulator. `baseline/control.json` is a
weak, valid example, not a recommended solution.

**Deliverable.** Submit one JSON artifact with 25 cubic B-spline coefficients for
each of the six prescribed channels. No executable, callback, predicted field,
or case-specific control is accepted. Follow the exact interface in `input/SPEC.md`.

**Run locally, from this participant directory:**

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -I workspace/smoke.py --artifact baseline/control.json --output workspace/smoke_score.json
```

**Objective.** Maximize audited coherent fidelity simultaneously across all
uncertainty families. A pass needs core fidelity at least 0.990, worst-family mean
at least 0.985, and worst individual case at least 0.980, with all hardware and
numerical audits satisfied. Resource efficiency breaks fidelity ties; evaluator
runtime is diagnostic, not a reward for writing a faster simulator. Coarse smoke
scores cannot certify passing.

**Resources.** Intended construction budget: one hour, four CPU cores, 4 GiB RAM.
Only Python 3, NumPy and SciPy are needed; no XMDS2 installation, network, or GPU
is required. Optimize at development resolution, then check refinement. The
deliverable is the designed control itself, not an implementation of a formula.

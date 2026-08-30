# Robust coherent matter-wave splitter — ratchet 1

Construct one smooth, bounded six-channel waveform that transports and coherently
splits a two-component nonlinear condensate in eight dimensionless time units.
The same waveform must work across the full public eight-parameter uncertainty
box. Complete two-dimensional complex-field fidelity matters, including relative
phase; matching densities alone is insufficient.

**Assets.** `input/SPEC.md` defines the equations, target, interface and scoring.
`input/protocol.json` contains all constants and control limits. Nine development
cases are in `input/public_cases.json`; `input/focus_regions.json` identifies
diagnostic joint-extreme regions without narrowing the uncertainty box.
`workspace/field_control.py` and `workspace/smoke.py` provide a NumPy/SciPy simulator.
`baseline/control.json` is the preceding generation's champion: physically valid,
but below this generation's fidelity requirements.

**Deliverable.** Write exactly `control.json` in the assigned writable output
directory. Submit the prescribed JSON coefficient arrays only: 25 cubic B-spline
coefficients per channel. No executable, callback, predicted field or case-specific
control is accepted. The participant package itself is read-only.

**Public diagnostic.** From the participant directory, replacing the output path:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -I -B workspace/smoke.py --artifact /path/to/output/control.json --cache-dir /path/to/output/cache
```

The command prints a diagnostic score and writes only to an explicitly supplied
cache directory. Without `--cache-dir`, references remain in memory. Optional
`--output` must point into the assigned writable output directory.

**Objective.** Pass with audited core fidelity >=0.990, worst-family mean >=0.985
and worst individual case >=0.980, satisfying all continuous-control certificates
and numerical audits. All legacy cases remain; joint-extreme coverage is stronger.
Resource efficiency breaks fidelity ties. Coarse scores cannot certify passing.

**Resources.** One hour, four CPU cores, 4 GiB RAM; Python 3, NumPy and SciPy only.
No network, GPU or XMDS2 installation is needed. The output is a designed control
artifact, not an implementation of a formula.

# Collective fluxoid search in perforated superconducting grains

Improve a strong CPU solver's stationary states in connected, narrow-bridge
superconducting grains with many coupled holes. Escape metastable hole-winding
and vortex allocations, rather than merely polishing a single local minimum.
The exact model is gauge-covariant finite-lattice, near-`Tc` Ginzburg–Landau with
prescribed physical vector potential. It is **not** equivalent to SuperConga's
self-consistent Eilenberger theory.

## Assets and interface

`input/MODEL.md` defines the energy and gradient; `input/gl_model.py` implements
the public API. `input/API.md` specifies the data contract. Two development
cases and numeric baseline/witness targets are in `input/cases` and
`input/development_targets.json`. `baseline/solve.py` is the previous successful
solver, with nonlinear conjugate-gradient relaxation and stochastic topological
mutations. All participant assets are read-only.

Write the submission to the designated **output artifact directory**, with
**`solve.py` at its root**. Run one case per process:

```sh
python OUTPUT_ARTIFACT_DIR/solve.py --input CASE_JSON --output RESULT_NPZ
```

Return exactly one full-grid complex array `psi` in the NPZ. The evaluator
independently recomputes energy and stationarity; submitted scores are ignored.

## Objective and limits

The supplied initial field is the exact frozen baseline state, not a requirement
to preserve its topology. Close its energy gap to a private attained lower-energy
**witness**, without any claim that the witness is a global minimum. Three
held-out cases form one collective-fluxoid family. Pass requires mean gap closure
at least **0.65**, worst-family closure at least **0.45**, no regression on any
case, and gradient RMS at most **0.002**. With one family, the two means coincide.
See `input/SCORING.md`.

Each case permits **60 seconds wall time and CPU time, one CPU core, 2 GiB memory,
256 MiB scratch, and a 4 MiB NPZ limit**. Startup and I/O count. Use Python standard
library, NumPy, and SciPy only; no GPU, network, external executables, private
assets, or state shared across cases. Runtime is reported separately from quality.

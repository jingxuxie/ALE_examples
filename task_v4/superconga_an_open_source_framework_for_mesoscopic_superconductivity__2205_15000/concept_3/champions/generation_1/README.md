# Active LDOS reconstruction

Run `python solve.py` with the JSONL session described in the participant API.
The entry point is standalone: it needs only Python, NumPy, SciPy, and the two
adjacent helper modules. It does not load labeled scenes or any saved state.

## Method

- Acquire 44 deterministic, spatially and spectrally distributed measurements.
- Enumerate all 46 vortex configurations using sparse-regularized nonlinear
  fits with exact resolvent-identity derivatives.
- Fit discrete supports containing four through seven signed impurities.
- Choose further measurements using disagreement between candidate scenes and
  local parameter-information gain. An independent query verifies an early
  reconstruction; otherwise, acquisition continues up to the 56-query limit.
- Resolve difficult fits with support exchanges, exact finite-strength
  single-site updates, the public clustered-support prior, and diverse restarts.

`physics.py` implements the supplied Hamiltonian. `inference.py` implements the
inverse search and experiment selection. The no-vortex case uses an equivalent
64-dimensional normal-state spectral decomposition for faster evaluations.

BLAS is restricted to one thread. An 83-CPU-second / 110-wall-second search
deadline leaves margin for returning a prior-valid estimate. The solver writes
only JSONL to stdout, diagnostics to stderr, and no files. No network, external assets,
compilation, or cross-episode persistence is used.

## Validation

The Hamiltonians for all 46 configurations match the public forward model.
Predictions, exact derivatives, zero-vortex spectra, and finite-strength
single-site updates were checked against the supplied simulator. Local protocol
tests use the supplied harness and its time, memory, query, and output limits.
Validation results are local diagnostics, not an official hidden-suite result.

The final train-plus-calibration run recovers all 12 public scenes, with support
F1 of 1.0, exact vortex configurations, and no protocol failures.
`validation_summary.json` records additional development coverage, resource
measurements, and hashes of the final solver sources.

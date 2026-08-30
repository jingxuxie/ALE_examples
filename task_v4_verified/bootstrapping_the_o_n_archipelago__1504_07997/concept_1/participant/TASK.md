# Extremal mixed-matrix spectrum recovery

## Mission
Improve the supplied baseline to recover an extremal atomic spectrum: all
continuum touching zeros and active isolated-point constraints, their null/OPE
directions, and positive spectral weights satisfying coupled measurements.
This is an explicit reduced 2x2 polynomial-matrix surrogate, **not** full 3D
conformal blocks or a reproduction of SDPB.

## Deliverable
Submit a standalone directory `output/` containing `solve.py` and any local
supporting files. One fresh process receives one JSON case on stdin and writes
one JSON result on stdout. Do not depend on files outside your submission or
use network access. `workspace/solve.py` is an editable starting point;
`baseline/solve.py` preserves the initial implementation.

From this participant directory:
`python output/solve.py < input/sample_01.json`.
The exact input/output schema, numerical guarantees, matching rules and limits
are in `input/FORMAT.md`. Input-only examples are in `input/sample_*.json`.

## Objective and resources
The hidden deterministic evaluation scores complete locations, sign-invariant
null projectors, positive weights and global residual consistency. It includes
near-coincident, multiscale, boundary, rotating-null and coupled cases.
Pass requires **core >= 0.90 and worst-family >= 0.80**, no protocol failures,
and at most 240 seconds total participant runtime; each case has 30 seconds
and 1 GiB memory. Accuracy is primary; runtime breaks ties.

Python 3.10, NumPy 1.21.5, SciPy 1.8.0, mpmath 1.3.0 and the standard library
are available. No cvxpy or external services are required. Work only from this
participant material; organizer files and hidden evaluation data are off limits.

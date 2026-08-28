# Solution

- `solve.py` implements the contract directly using NumPy, with no external interpolation package.
- It handles compact/full force constants and nonconsecutive supercell representatives, averages every supplied tied shortest-vector phase, and retains nonzero reciprocal-vector sums and atom-zero-relative phases.
- It evaluates all three lattice origins, restores their atom and Cartesian axis order, and averages complex amplitudes before calculating strengths.
- Mode contraction uses eigenvector columns without conjugation, inverse-square-root masses, and strictly positive-above-cutoff frequencies; excluded band triples are exactly zero.

## Validation

- Ran the executable NPZ interface on `participant/input/smoke.npz`; both output fields have the required shapes, dtypes, and finite values, with nonnegative strengths.
- All eight tests in `test_solution.py` pass: independent direct-sum oracles, randomized multi-triplet cases, full/compact storage, supercell and primitive reordering, nonzero reciprocal sums, all six triplet permutations, time reversal, origin shifts, mass scaling, Gamma points, strict cutoff boundaries, and empty batches.
- Against independent direct summation on the public smoke input, relative L2 errors are approximately `8.9e-16` for the reciprocal tensor and `9.2e-16` for strengths.
- Benchmarked synthetic inputs through `P=8, S=256` and `P=16, S=128` with one thread; measured interpolation times were approximately 0.18 s and 0.54 s per triplet, respectively.

Run: `python solve.py INPUT.npz OUTPUT.npz`

Tests: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python test_solution.py`

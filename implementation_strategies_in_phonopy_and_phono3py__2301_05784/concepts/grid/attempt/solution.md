# Solution

Run `python solve.py INPUT.npz OUTPUT.npz`. The solver uses NumPy and the Python
standard library and writes exactly the five contracted output arrays.

Implemented:
- Exact integer adjugates and modular quotient keys for arbitrary grid matrices,
  representative orderings, and periodically translated addresses.
- Three-dimensional lattice reduction followed by radius-bounded sphere
  enumeration, with no fixed image box or multiplicity. Integer basis changes
  preserve original-basis shifts; extended precision is used for geometry.
- The prescribed shortest-diagonal, six-tetrahedron periodic mesh, normalized
  independently for every branch.
- Analytic piecewise cubic cumulative integrals and quadratic DOS, including
  repeated corner energies and exact flat-tetrahedron point masses. Local
  polynomial accumulation on a threshold interval tree avoids histogram
  smearing, unstable global polynomial cancellation, and a full
  tetrahedron-by-threshold array.

Tested:
- `python test_solution.py`: independent SciPy B-spline integrals; analytic
  repeated-energy identities; narrow features, irregular thresholds, negative
  energies, one-point grids, exact cumulative jumps; arbitrary quotient
  representatives; exhaustive geometry comparisons, boundary ties, large
  shears, translations, and unimodular basis changes. All checks pass.
- The supplied example agrees with the independent spectral reference to
  maximum absolute errors of about 4.1e-15 (cumulative) and 1.4e-13 (DOS).
- `python benchmark_solution.py`: a generated non-diagonal grid with 105,840
  points, four branches, and 414 thresholds, including a narrow optical branch
  and repeated energies. The latest measured solve took 1.98 seconds with
  190,772 KiB peak process RSS. Selected thresholds agree with direct
  extended-precision integration to below 1e-16 absolute cumulative error and
  1.5e-15 maximum DOS error normalized by the branch's sampled peak (or one).
- The two-path CLI and its output array shapes, dtypes, finiteness, CSR image
  offsets, and cumulative monotonicity are checked on the public smoke input.

These timings and errors are local test measurements, not private-case results.

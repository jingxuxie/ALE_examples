# Robust Josephson-junction geometry solver

## Run

```sh
python /absolute/attempt/solve.py --input /absolute/request.json --output /absolute/result.json
```

The required implementation files are `solve.py`, `geometry.py`, and
`fast_physics.py`. NumPy, SciPy, threadpoolctl, and the supplied
`participant/workspace/physics.py` are required. The helper is located relative
to either the current working directory or the attempt directory. No writes to
the participant directory are needed.

The result contains exactly `schema_version`, the original `request_id`, and
`geometry`. Both contact masks are binary, row-major arrays with the requested
dimensions. The output path is honored and replaced atomically.

## Design method

- Search triangular, rounded, and multiple-bend periodic channels on the actual
  requested lattice. Refine amplitude, width, corner rounding, periodic width
  variation, and a third harmonic of the centerline. Include the design found
  and independently validated on the public example as one starting candidate;
  evaluate it afresh for each request rather than assuming it generalizes.
- Construct both contacts as boundary graphs, with reflection symmetry enforced
  before rasterization. Check every candidate with the authoritative fabrication
  validator, including periodic separation and median-filter roughness.
- Evaluate the full-scale BdG Hamiltonian, not a coarse or rescaled substitute.
  Initially screen three operating points; rerank candidates over a 3-by-3
  chemical-potential/Zeeman grid before local boundary refinement.
- Reject trivial phases. Screen finalists on a 9-by-5 topology grid including
  operating-region boundaries. Compare surviving candidates at 21 operating
  points, first completing five-momentum scans and then spending the remaining
  budget on nine-momentum scans and additional samples near the estimated
  minimum on the evaluator's 51-point momentum grid.
- Optimize half the mean gap plus half the worst gap. These public-region
  samples approximate robustness; the private operating points and anchors are
  neither available nor assumed.

## Efficient physical evaluation

At Bloch momenta zero and pi, longitudinal reflection combined with spin-X
commutes with the Hamiltonian. Particle-hole conjugation exchanges its two
reflection sectors. Consequently the product of determinant signs of the
positive-reflection Hamiltonian at zero and pi gives the class-D invariant.
The antiperiodic reflection includes a minus sign on wrapped columns. An atomic
trivial Hamiltonian fixes the sign convention. The minimum absolute eigenvalue
of this half-sized sector also gives the full endpoint excitation gap.

Interior momenta use the full sparse Hamiltonian. Shift-invert solves use
single-threaded sparse LU and check eigenvector residuals, falling back to
pivoted factorization if necessary. Topology-only checks use pivoted LU.
Scalar spectra are cached across screening and refinement stages.

The solver uses two single-threaded worker processes and reserves time before
the request's wall deadline. For the standard 1200-second request, its search
deadline is 1120 seconds. It writes a schema-valid baseline checkpoint before
searching and selects a topology-screened result whenever one is available.

## Reproducible validation

`verify_submission.py` independently uses the supplied forward helper, its
eight-state eigensolver, all 51 momenta, and its Pfaffian invariant. It compares
the submission with the supplied baseline at three deterministic held-out
points inside the public operating region:

```sh
python verify_submission.py --input ../participant/input/example.json \
  --geometry example_result.json --output validation.json
```

The exploration scripts and their logs are development diagnostics, not solver
dependencies or stored solutions.

## Observed full-grid checks

On the provided example, independent 51-momentum, eight-band forward checks
at the three held-out operating points give:

| Quantity | Original zigzag | Returned geometry |
| --- | ---: | ---: |
| Gap at mu=11.355, B=1.243 meV | 0.086551 | 0.224156 |
| Gap at mu=13.185, B=0.713 meV | 0.102024 | 0.187594 |
| Gap at mu=14.455, B=1.064 meV | 0.086422 | 0.220701 |
| Robust gap, meV | 0.089044 | 0.199205 |

Both geometries have Pfaffian invariant -1 at all three points. The returned
geometry passes every manufacturing check, with 134.16 nm minimum separation
and 10 median-filter flips. This is a 2.237-fold robust-gap improvement on
these public-region checks, not a claim about unavailable private scores.
The executable completed the provided request within its 1200-second budget.
Full measurements are in `validation.json`; `example_result.json` contains
the tested contact masks.

An additional full-scale synthetic request uses a 980 nm period, 1300 nm
transverse span, and fixed covered chemical potential of 15 meV. With its
test budget reduced to 600 seconds, the solver finishes in 554.3 seconds.
Independent 51-momentum checks give robust gaps of 0.085278 meV for the
original zigzag and 0.171519 meV for the submission (2.011-fold improvement).
All three submission Pfaffians are -1. Fabrication passes with 107.70 nm
minimum separation and six median flips. See `synthetic_request.json`,
`synthetic_result.json`, and `synthetic_validation.json`.

Finally, the public calibrated seed and its period-scaled version are checked
on both grids. Reflection-sector topology agrees with the supplied Pfaffian
implementation; accelerated gaps at zero, 0.37*pi, and pi agree with the
eight-state helper to within 4.6e-14 meV. These checks are recorded in
`seed_validation.json`. Both output JSON files also pass exact-key, size,
and authoritative mask-loading checks, and the implementation passes Python
bytecode compilation.

# Bounded counterexample search: rejected as robustly solved

## Decision

No natural counterexample was found in four representative physical challenges.
Reject this pilot as robustly solved by the existing ultima-alpha submission
within the tested region. No ratchet participant or fresh ratchet heldout set
was created: there is no demonstrated failure to justify either. This is a
bounded empirical result, not a proof for every possible input.

The original `participant/`, `attempt/`, initial manifest, initial inputs,
references, baselines, scorer, and initial pilot score are unchanged. Their
SHA256s are recorded in `protected_initial_sha256.json` and checked after the
search. All new inputs and labels are private; none were written into attempt.

## Measured evidence

All columns of each physical spectrum were supplied; no branch subsampling,
random energies, altered score normalization, or tighter tolerances were used.
N is full-BZ grid size, B physical branch count, M threshold count. Oracle and
submission each had the original 180-second and 8192-MiB limits, with one
OpenMP/OpenBLAS thread. RSS is peak resident **KiB**, not address-space use.

| Physical workload | N | B | M | Oracle s | Submission s | Submission RSS KiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Non-diagonal AlN full BZ | 1,048,576 | 12 | 27 | 85.89 | 11.09 | 991,748 |
| Highly oblique anatase TiO2 | 73,728 | 18 | 57 | 25.02 | 11.64 | 151,968 |
| SnO2 4096-by-8-by-4 long-wave grid | 131,072 | 18 | 56 | 36.30 | 6.30 | 215,680 |
| Complex-cell Zr3N4 optical spectrum | 131,072 | 42 | 35 | 45.68 | 14.81 | 179,180 |

Mean core quality: **0.9999999999999946**. Worst individual geometry/spectral
component: **0.9999999999999813**. All four executions succeed. Total submitted
runtime is 43.83 seconds. Geometry image sets and canonical order match exactly
on all 1,024 chosen queries. Reference image multiplicities reach 4, 2, 4, and
3 respectively, with 132, 85, 166, and 128 tied queries.

Largest absolute discrepancies across the four cases are 9.11e-15 for
cumulative, 5.51e-14 for DOS, and 6.70e-16 for squared distance. These are
roundoff-level residuals, not a scientific failure. Raw component errors and
measured weak-baseline errors remain available in `report.json`.

Reference checks include CDF endpoints/monotonicity, finite and nonnegative
spectra, and 24 independently certified closest-image queries per challenge.
The latter use an exhaustive singular-value-bounded search in the known
original physical basis, not the submitted solver. `summary.json` records the
full image-array comparisons and numerical discrepancy maxima.

## Why these cases, and why stop

Inspection of `attempt/solve.py` and `solution.md` identified two plausible
stress points: its materialized six-tetrahedron connectivity and per-branch
energy/position arrays at full-BZ scale; and reduced-basis closest-image
enumeration with degenerate or very anisotropic geometry. Its spectral path
already uses stable local polynomial accumulation on a threshold tree, rather
than a histogram, broadening, or unstable global power sums.

The million-point case raises measured memory to about 969 MiB but remains far
below 8 GiB, and the submitted algorithm is faster than the official reference.
The TiO2 reciprocal basis has condition number 759.44, versus 3.95 in the
original primitive representation. This is an explicitly disclosed legitimate
unimodular basis change, **not** an assertion that the physical material has
intrinsic anisotropy 759. The physical acoustic/optical datasets contain exact
and near branch degeneracies; selected adjacent gaps below 1e-7 THz number
98,366, 495, 110,911, and 3,180 respectively. The SnO2 thresholds additionally
probe the physical zone-center acoustic region. None of these stresses reveals
an error. Further arbitrary size, shear, or tolerance escalation would not be
an honest consequence of this bounded search, so the search stops.

The official graphene-Siesta example was screened but excluded before creating
a scored input. Its one force file lacks an explicit displaced structure, and
the available reader exhibits obsolete setters/unit parsing incompatibilities.
An inferred displacement/force association would not provide trustworthy
physics provenance. The fully specified TiO2 displacement/force fixture replaces
that source candidate; graphene is not counted as a solver failure.

## Provenance and reproduction

All primary references use the unchanged pinned adapter
`private/reference/solve.py`, phonopy 2.43.4, phono3py 3.19.2, and spglib 2.5.0.
Official fixture SHA256s, harmonic force-constant hashes, basis changes,
frequency ranges, and input/reference hashes are stored in each new case JSON.
Initial exact source revisions and module hashes remain in the protected
`private/reference/provenance.json`. Baselines and submissions run through
unchanged shared `author/evaluation.py::sandbox_run`; scoring calls unchanged
`private/evaluator.py::score_case`.

New manifest: `private/challenge_pool/manifest_search_01.json`, with split
`search`. Case NPZs and metadata live under
`private/challenge_pool/bounded_search_01/`. Execution artifacts, full results,
and preservation evidence live here. `run.py` is the four-case generation and
measurement driver; it resumes interrupted work but refuses to overwrite a
completed search. Its source-and-execution phase took 340 seconds, excluding
interactive source inspection and the rejected fixture probes.

To replay the existing submitted solver with the same isolation and scorer,
run from the task target (the report path must be new and private):

```
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python -B concepts/grid/private/reference/bounded_search_01/replay.py --output concepts/grid/private/reference/bounded_search_01/replay_report.json
```

The replay command may require permission to launch bubblewrap outside an
outer sandbox; it does not fall back to unisolated solver execution.

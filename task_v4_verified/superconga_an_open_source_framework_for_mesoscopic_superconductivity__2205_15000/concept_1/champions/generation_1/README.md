# Pinned-grain GL solver

This targets the prescribed-field finite-lattice Ginzburg–Landau benchmark, not
self-consistent Eilenberger theory or electromagnetic screening.

## Run

```sh
python solve.py --input /path/to/case.json --output /path/to/result.npz
```

The implementation is self-contained and requires only Python, NumPy, and SciPy.
It does not import participant files, read other cases, use external executables,
or retain state across invocations. The output is exactly one `complex128` array,
`psi`, with the input grid shape and zeros on inactive sites. The exact requested
output path is used, including when it has no `.npz` extension.

## Search

- Reproduce the two public baseline starts with the original full-grid objective
  and L-BFGS-B settings; retain the lowest-energy incumbent.
- Represent the same quadratic GL energy by a Hermitian sparse matrix, preserving
  the prescribed links and omitted-link boundary conditions exactly.
- Relax candidates with nonlinear conjugate gradients and safeguarded searches
  on the exact quartic energy along each search direction.
- Combine independent complex starts with vortex insertion, removal, relocation,
  hole-winding changes, local phase disturbances, and low-energy field crossover.
- Use temporary pin softening or heating and a small basin-hopping population to
  explore alternative configurations. Evaluate all candidates with the original
  coefficients, not with the temporary search objective.
- Finish with tight L-BFGS-B relaxation. Retain a separate stationary fallback.

Vortex diagnostics use covariant bond phases and the supplied plaquette flux.
No assumptions about the input gauge, case identifier, or uniform bulk flux are
used. The search is heuristic: attained energies are not ground-state certificates.
Only the explicit onsite lower bound is used to recognize simple certified cases.

## Resource Handling

BLAS and OpenMP thread counts are set to one before numerical imports. The budget
tracks both wall and process CPU time from startup, targets at most 57 seconds,
and reserves approximately three seconds for final relaxation and output. A
repeatedly recovered, stable incumbent permits earlier termination. No scratch
files are created by the solver; only the requested output is written.

## Validation

`validation.json` records independently recomputed development energies, gradient
RMS values, output checks, and measured subprocess runtimes. All three development
witness energies are recovered to numerical precision, without treating those
witnesses as proven minima.

Additional checks cover analytic derivatives, large pure-gauge transformations,
reversed magnetic fields, disconnected domains, normal states, single-site
domains, and unstable zero initial fields. Resampled development grids up to
71 by 74 sites exercise the larger-grid time and stationarity limits. These are
public-asset stress tests, not held-out benchmark results.

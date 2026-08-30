# Parity-conserving variational MPS solver

Run the submitted solver with the required interface:

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

The output is an uncompressed NPZ containing only `A0`, ..., `A{n_sites-1}`.
The solver uses the supplied finite, padded-oscillator Hamiltonian without
changing its cutoff or coefficients. All optimization and output tensors
preserve the requested global parity and requested bond cap.

## Method

- Diagonalize each local Hamiltonian within its two parity blocks and initialize
  a parity-projected, self-consistent product state.
- Grow the MPS through small bond dimensions, then optimize with single-site
  Davidson sweeps and an expanded two-site update.
- Accelerate sweeps by aligning MPS gauges and testing an energy-controlled
  extrapolation. Keep the lowest-energy valid state encountered.
- Reconsider the numbers of even and odd bond states. Candidate one-channel
  transfers undergo alternating variational refinement in an enlarged bond
  space and are accepted only when they lower the energy. This avoids freezing
  a merely Schmidt-weight-optimal parity allocation.
- Use a limited early boundary-allocation check for short requests with smaller
  caps, while prioritizing ordinary convergence for larger caps.
- Check both CPU and wall deadlines throughout optimization and reserve time
  for basis restoration, serialization, and process exit.

## Implementation

`solve.py` is the entry point and `solver.py` controls optimization. The production
dependencies are `contractor.py`, `optimizer.py`, `fast.py`, `sweeps.py`,
`bondsearch.py`, `newpair.py`, `relaxation.py`, and `native.py`.

`native_core.so` is an included Linux x86-64 Davidson kernel; its complete source
is `native_core.c`. It calls the installed SciPy BLAS/LAPACK functions in-process,
uses one execution thread, and requires no runtime compilation or subprocess.
A NumPy/SciPy fallback is used if the native library cannot be loaded. The
fallback can also be selected with `MPS_PYTHON_ONLY=1`.

The included native library is built with:

```sh
gcc -O3 -ffast-math -fno-finite-math-only -std=c99 -fPIC -shared native_core.c -o native_core.so -lm
```

No precomputed state, case identifier, network access, or cross-request cache is
used by the solver. The experiment files are validation records, not inputs to
optimization.

## Validation

```sh
python experiments/checks.py
MPS_PYTHON_ONLY=1 python experiments/checks.py
python experiments/benchmark.py
```

The numerical checks compare native and NumPy local eigensolvers and compare
both parity sectors of a small chain against dense exact diagonalization.
The benchmark driver launches independent CLI invocations under the stated CPU,
address-space, and output-file-size limits, then validates and recomputes each
MPS energy using the public contractor. It tests the three supplied examples
and twelve additional coefficient profiles constructed within the advertised
ranges, at both budgets.

Detailed results are in `experiments/validation_results.json`,
`experiments/checks_result.json`, and `experiments/fallback_checks_result.json`.
All 30 resource-limited runs pass. Maximum measured CPU times are 5.828 seconds
and 39.780 seconds for the two budgets; peak resident memory is 74.3 MiB.
Native/NumPy local-solver energies agree within `2e-14`; the small-chain exact
energy checks agree within `9e-16` in both parity sectors.

Public examples, using energies recomputed from the output tensors:

| Case | Frozen baseline, 6 s | Submission, 6 s | Submission, 40 s |
| --- | ---: | ---: | ---: |
| Symmetric | 27.845578383255 | 27.845578383257 | 27.845578383255 |
| Odd | 22.528477943640 | 22.528468850605 | 22.528468850599 |
| Nonuniform | 24.337353189147 | 24.337353042963 | 24.337353042963 |

The six validated public-example NPZ files are retained under `experiments/`.
Other benchmark states were removed to keep the complete directory below the
submission-size limit. They can be regenerated with the benchmark driver.
The hidden evaluator and reference energies were not provided; no hidden score
is claimed.

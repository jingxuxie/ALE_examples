# Noisy gauge simulator solver

`solver.py` provides the required `solve(case: dict) -> dict` entry point. It needs
only NumPy and SciPy and does not read external data, use the network, or write
files during a solve. It also accepts a case on standard input and writes the
result as JSON on standard output:

```sh
OPENBLAS_NUM_THREADS=1 python solver.py < case.json > result.json
```

## Numerical method

- Fit all three spectral models with bounded, multistart weighted least squares,
  analytic Jacobians, and the prescribed model-selection penalty.
- Construct the complete 64-dimensional Hamiltonian and observables in the
  specified most-significant-bit-first tensor order.
- Cluster energies and all ordered energy-pair gaps using the two prescribed
  first-value tolerances. Retain both frequency signs and elastic transitions.
- Form the correlated matter and link channels separately. Assemble the full
  sparse dissipator by summing equal-frequency amplitudes before their outer
  products, preserving degenerate-transition interference.
- Evaluate the supplied independent audit bath directly. For predictions,
  exponentiate invariant blocks of the full Liouville-space generator, retaining
  the coherent phases throughout the full time interval. No particle-number or
  gauge-sector projection, state renormalization, or steady-state substitution
  is used.
- Predict every feasible action and minimize the specified trapezoidal risk,
  measuring fidelity against the unprotected ideal Hamiltonian.

## Local validation

Validation uses the public example and locally constructed synthetic cases:

- Independent Kronecker-product Hamiltonians agree exactly; ideal Hamiltonian
  commutators with all three gauge constraints vanish.
- Explicit jump-by-jump audit calculations agree to approximately `1e-15`
  relative error, including an exactly degenerate Hamiltonian.
- Independent sparse matrix-exponential propagation agrees below `1e-10` at
  short and full-duration sample times; direct unitary propagation also agrees
  below `1e-10` when the dissipator is zero.
- All spectral families and parameter-boundary cases recover noiseless test
  spectra with relative error below `1e-6`.
- Symmetric and zero-Hamiltonian stress cases preserve trace within `1e-8`
  and positivity within `1e-8`, including maximal-rate baths and Liouville
  blocks of dimension 1024.

With one BLAS thread, the public example takes about one second on the local
machine; the complete degenerate stress cases take about two seconds or less.

# Noisy gauge simulator submission

`solver.py` exports `solve(case: dict) -> dict` and requires only NumPy and SciPy.
It can also read a case from standard input or a filename and write its JSON
answer to standard output:

```sh
python solver.py path/to/case.json > result.json
```

## Numerical method

- Bounded multistart nonlinear least squares, with analytic Jacobians, fits all
  three bath families and applies the prescribed parameter-count penalty.
- The Hamiltonians and observables use the full 64-dimensional computational
  basis, with the initial state's specified Gauss-law sector defining violations.
- Each full implemented Hamiltonian is diagonalized. Energy and frequency
  clusters follow the first-value rule, and frequency means include all ordered
  eigenvector pairs before removing numerically zero channel amplitudes.
- Frequency-resolved channel Gram matrices assemble a sparse Lindblad generator
  in the energy basis. Equal-frequency interference, independent species,
  collective signs, elastic jumps, and the three activity bins are retained.
- Sparse matrix-exponential actions evolve the complete density matrix without
  projection or renormalization. Fidelity uses the independently evolved ideal
  state, and action selection integrates the specified gauge/fidelity risk.
- Audit calculations use their supplied bath rather than the calibration fit.

## Local validation

Run `python validate.py` while this submission is beside the public participant
directory. It checks the tensor-product Hamiltonian, Gauss-law commutation,
noiseless bath recovery including parameter boundaries, explicit channel-by-channel
audit calculations, degenerate and zero-frequency interference, trace preservation,
unitality, Hermiticity, positivity, the unitary limit, and the example's JSON and
feasibility contract. These checks use only public inputs and synthetic variations.

The public example completed in approximately 1.2 seconds with one BLAS thread
and about 76 MB peak resident memory. Its selected action is `flat_low`. Independent
generic and degenerate audit calculations agree at relative errors below 1e-14.

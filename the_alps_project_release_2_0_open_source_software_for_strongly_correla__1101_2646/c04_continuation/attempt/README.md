# Matrix spectral reconstruction

Run the offline service with:

```sh
python solve.py --input request.json --output result.json
```

The entry point implements the supplied interface contract. It requires only Python, NumPy,
and SciPy. No network, stored training data, or auxiliary executables are used.

## Reconstruction

- Frequencies and moments are normalized together. All operations retain the
  full complex orbital matrices, including noncommuting orbital coherence.
- Discrete measures are reconstructed using Hermitian, shared-pole rational
  fits and positive block-Loewner realizations. Rank stability and independent
  rational checks guard against treating a resolved continuum as a small bath.
- Continuous measures use an ensemble of matrix rational continuations, both
  directly and after a moment-normalized Dyson transformation. Conformal maps,
  inferred spectral edges, held-out sample checks, and adaptive approximation
  orders stabilize continuation without treating the supplied error bound as
  an independently sampled noise variance.
- An optional low-harmonic matrix band fit is accepted only after checking
  every supplied imaginary-frequency matrix. Its retarded propagator is
  evaluated by a matrix-polynomial contour integral. Other band structures
  retain the general rational reconstruction.
- Matrix loss operators, rather than elementwise imaginary parts, determine
  causality. The returned self-energy always uses the stipulated full-matrix
  Dyson inverse and the supplied bare Hamiltonian.

BLAS/OpenMP thread counts are fixed to one. Model refinement has an elapsed-time
budget that leaves margin below the 120-second per-request allowance.

## Tests

```sh
python -m unittest -v test_solver
```

The regression tests cover the CLI, discrete spectra, a larger matrix bath,
complex orbital rotations, static self-energy shifts, smooth bands, a contour
integral against dense quadrature, matrix spectral positivity, and Dyson
consistency. Additional synthetic stress benchmarks and experimental logs are
kept in this directory; they are not needed to run `solve.py`.

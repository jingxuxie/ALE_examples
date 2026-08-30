# Low-order Hamiltonian reconstruction

This submission recovers the missing transfer amplitudes from the public CAS
energies, then diagonalizes the recovered seniority-zero Hamiltonian. It does
not fit the labels or use a statistical extrapolation, family-dependent learned
parameters, private files, or network resources.

## Singleton inversion

For one virtual orbital, the CAS basis consists of the occupied reference and
the `O` states replacing one occupied pair. Occupied-occupied transfers vanish,
so its reference-shifted Hamiltonian is an arrowhead matrix with diagonal
`(0, g_1, ..., g_O)` and couplings `-a_v u_i`. If the supplied singleton
correlation is `c_v`, its Schur-complement equation gives

```text
a_v^2 = -c_v / sum_i [u_i^2 / (g_iv - c_v)].
```

All quantities on the right are supplied features. The positive square root
fixes every occupied-virtual transfer using the public positive source profile.

## Pair inversion and independent triple checks

For each virtual pair, only one signed transfer `t` remains unknown. Construct
the known pair-CAS matrix `H0` with that edge zero, and its transfer operator
`B`, giving `H(t) = H0 + t B`. For the supplied absolute ground energy `E`,
solve the small generalized eigenproblem

```text
(E I - H0) x = t B x.
```

Filter its finite real eigenvalues by the supplied edge sign, the generator's
magnitude bounds `[0.012, 0.28]`, and the requirement that `E` is the lowest
eigenvalue, rather than an excited state. A scalar root-search fallback is
included. If multiple physical roots remain, supplied triple CAS energies
disambiguate them by enumerating the at-most-three pair choices in each triple.

After reconstructing all edges, recompute every supplied singleton, pair, and
triple CAS energy. A discrepancy above `1e-9` raises an error instead of silently
emitting an inconsistent prediction. Full-space diagonalization has dimension
at most `binomial(12, 3) = 220`.

The submitted signed tail is exactly

```text
E_full(reconstructed H) - reference_energy - truncated_correlation.
```

## Reproduction and validation

Run from this output directory with the supplied system runtime:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B reconstruct.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B validate_synthetic.py
PYTHONDONTWRITEBYTECODE=1 python -B verify_artifact.py
```

`reconstruct.py` accepts `--assets`, `--output-directory`, and `--splits`.
It reads only the public generator and participant data. Label arrays are
excluded from reconstruction inputs and used only for post-prediction metrics.
`reconstruction_report.json` records full labeled-split errors and unlabeled
test CAS consistency diagnostics. `synthetic_validation_report.json` compares
inferred transfers and tails against 96 independently generated Hamiltonians,
balanced across all six families, both pair counts, and all four virtual counts.
The independent RNG seed is a participant-chosen seed, not a release seed.

`predictions.npz` is the final submission. Its only arrays are the 288 test IDs
as Unicode `U32` and their signed tails as `float64`. Labeled-split prediction
archives, source scripts, and validation reports are supporting artifacts.
`artifact_verification.json` records the archive checks and SHA-256 hashes of
the final submission and the unchanged public input archives.

# Premature-screening witness

The submitted artifact is `witness.json`. The supplied complete checker reports
`valid: true`, `passed: true`, and `core_score: 1.0`.

| Diagnostic | Recomputed value | Requirement |
| --- | ---: | ---: |
| Largest absolute triple increment | 0.3507257245 microEh | <= 1 microEh |
| Absolute missing tail | 63.33264208 microEh | >= 50 microEh |
| Tail / largest absolute triple | 180.5759819 | >= 100 |
| Reference determinant weight | 0.9826574447 | >= 0.95 |
| Seniority-zero spectral gap | 0.9648215216 Eh | >= 0.4 Eh |
| Diagonal reference excitation margin | 0.9657140147 Eh | >= 0.6 Eh |

All 35 triple increments meet the gate, so no quadruple is generated. The tail
is positive: the full energy is -3.0385009119727138 Eh, while the third-order
truncation is -3.0385642446147942 Eh. The fourth-order signed sum alone is
62.50068646 microEh.

## Search and validation

`search.py` uses the supplied fixed constants, exact subsystem ground-state
eigenvalues, Hellmann-Feynman derivatives, and bounded multistart SLSQP. Only
the 42 permitted virtual-block coefficients vary. The search stops once a
passing candidate has been saved; the final JSON contains no claimed metrics.

- `validation.log` compares the search implementation with the public model
  and checks directional derivatives against finite differences.
- `search.log`, `checkpoint.json`, and `trial_*.npy` preserve the search history.
- `check_summary.json` is the supplied checker's complete-subset summary.
- `check_details.json` also records all 128 subset energies and increments.
- `verification.json` records direct alternating-sum, nested-subspace,
  eigensolver-agreement, coefficient-bound, and artifact-size checks.

The full-sector eigensolver algorithms agree to 1.20e-14 Eh, the public
eigenvector residual is 1.29e-15 Eh, and the MBE closure error is 4.44e-16 Eh.
The artifact is a regular 2668-byte JSON file with exactly symmetric,
zero-diagonal matrices satisfying all coefficient bounds.

To repeat the public validation from the participant directory:

```sh
python -B workspace/check.py /path/to/output/witness.json --details
```

All search and validation artifacts reside in the supplied writable output
directory. The participant assets were not changed; no network or hidden
evaluator artifacts were used.

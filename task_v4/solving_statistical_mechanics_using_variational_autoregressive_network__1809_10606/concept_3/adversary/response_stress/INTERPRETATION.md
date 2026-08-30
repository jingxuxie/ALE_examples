# Post-score interpretation of the frozen stress grid

No further queries, fitting, model changes, or target changes were made after
these scores. The sealed queries, labels, and prediction arrays remain unchanged.

## Main result

The best previously fitted predictor (`latent_fit_weak`, meaning weak
regularization) still satisfies all three original limits over the 120-case
stress set: mean KL 0.0027333, worst-family mean KL 0.0034888, and maximum TV
0.107176. One individual KL is 0.03051; this does not violate the original
aggregate KL gate. There are no TV failures for this model.

`latent_fit_strong` means stronger regularization, not a stronger predictor.
It meets the aggregate KL limits but fails the maximum-TV limit on 17 cases.

| Family | Weak-penalty fit: TV failures | Strong-penalty fit: TV failures | Empirical recipe: TV failures |
|---|---:|---:|---:|
| Zero field | 0/30 | 7/30 | 17/30 |
| Readout-local fields | 0/30 | 2/30 | 13/30 |
| Neighbor-column fields | 0/30 | 4/30 | 18/30 |
| Remote-column fields | 0/30 | 4/30 | 21/30 |

The empirical recipe is exactly the original frozen algorithm on the first two
families. It already fails materially on those 60 cases: mean KL about 0.127514,
maximum TV about 0.703996, and 30 TV failures. Its failure is therefore not an
artifact of the separately preregistered nonlocal extension. The latter uses
no fitting and has another 39 TV failures among 60 nonlocal-field cases.

## Meaningful response examples

- `stress_089`: beta 2.5; readout column 9; four alternating unit fields in
  neighboring column 10. The actual field-induced distribution change is TV
  0.65723. The weak-penalty fit has TV error 0.10718, its largest error. Public
  field-importance ESS is only about 54 at the beta-1 training ensemble.
- `stress_106`: beta 3; two opposite half-unit fields within readout column 9.
  The strong-penalty fit has TV error 0.18673; the two frozen fits disagree by TV
  0.17402. This is sensitivity to the estimator/regularization, not a demonstrated
  inability of the available data to support accurate prediction.
- `stress_113`: beta 3; four alternating unit fields in the column next to the
  readout. The empirical nonlocal extension predicts positive majority with
  probability about 0.999999, versus an exact value about 0.0000572. This is a
  large physical response error, not arbitrary precision tightening.

## Finite-data uncertainty versus algorithmic limitations

The evidence primarily implicates excessive regularization and unreliable
empirical temperature extrapolation: a different already-frozen estimator,
trained on exactly the same observations, remains accurate throughout this grid.
This does not prove identifiability or establish confidence intervals.

Five stress cases have a field-importance ESS below 128, and the best fit's
largest error occurs in one of them. That is a meaningful warning about limited
observational support for some strong interventions. However, this ESS measures
the empirical reweighting problem, not uncertainty of the exact latent-likelihood
fit. It cannot establish an irreducible finite-data error floor.

No refitted bootstrap or posterior uncertainty analysis was performed. Eighteen
independent dense-transfer comparisons agree within 3.34e-16 in probability, so
the recorded macroscopic discrepancies are not explained by forward numerical
error. Do not infer that the successful weak-penalty fit must fail somewhere
else; no additional query search was conducted.

For replay, use `queries.json` and `true_probabilities.npz`. `RESULTS.json`,
`per_query_scores.json`, and `SUBSET_SUMMARY.json` retain the full breakdowns.
The original live participant assets, evaluator, targets, and status were not
modified.

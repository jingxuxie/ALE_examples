# Frozen-model response stress audit

120 cases, seed 20260828, preregistered before opening material parameters or observing stress scores.
Betas: 1.3, 1.6, 2, 2.5, 3. Each beta has six cases each of zero field, readout-local field, neighboring-column field, and remote-column field (distance >=4).
At most four visible sites are perturbed, with amplitudes <=1. All eight columns eligible for six-visible-spin readouts are covered.

| Frozen predictor | Mean KL | Worst family mean KL | Max TV | Cases KL>.02 | Cases TV>.12 | Meets original limits on stress set |
|---|---:|---:|---:|---:|---:|---|
| latent_fit_weak | 0.002733 | 0.003489 | 0.107176 | 1 | 0 | True |
| latent_fit_strong | 0.019484 | 0.021739 | 0.186731 | 37 | 17 | False |
| empirical_log_bridge | 0.535873 | 1.147594 | 0.999999 | 107 | 69 | False |

## Failure families

### latent_fit_weak
- zero_field: mean KL 0.002330, max TV 0.064044, 0 TV failures / 30 cases.
- readout_field: mean KL 0.002204, max TV 0.063097, 0 TV failures / 30 cases.
- neighbor_field: mean KL 0.003489, max TV 0.107176, 0 TV failures / 30 cases.
- remote_field: mean KL 0.002910, max TV 0.089382, 0 TV failures / 30 cases.

### latent_fit_strong
- zero_field: mean KL 0.021739, max TV 0.165002, 7 TV failures / 30 cases.
- readout_field: mean KL 0.016038, max TV 0.186731, 2 TV failures / 30 cases.
- neighbor_field: mean KL 0.020356, max TV 0.141983, 4 TV failures / 30 cases.
- remote_field: mean KL 0.019804, max TV 0.160998, 4 TV failures / 30 cases.

### empirical_log_bridge
- zero_field: mean KL 0.111595, max TV 0.360782, 17 TV failures / 30 cases.
- readout_field: mean KL 0.143433, max TV 0.703996, 13 TV failures / 30 cases.
- neighbor_field: mean KL 0.740869, max TV 0.999999, 18 TV failures / 30 cases.
- remote_field: mean KL 1.147594, max TV 0.999691, 21 TV failures / 30 cases.

## Interpretation and limits

The original empirical bridge supports only fields within the readout. Its original frozen recipe is used on the 60 zero/local-field cases; the remaining 60 use the preregistered no-fit importance-reweighting extension, not a newly fitted estimator.
Single-case KL>.02 is diagnostic only: the live task's KL gate is an average. Stress-set scores do not alter any live task or target.
Prediction sensitivity to regularization and cold/nonlocal extrapolation can suggest weak identification from finite warm-temperature observations. It is not proof of irreducible finite-data uncertainty; neither estimator has been refitted or bootstrapped.
Independent dense-transfer comparisons agree to the recorded residual; observed macroscopic failures are not explained by transfer numerical error.
Importance ESS diagnoses field-tilt support at the two observed ensembles, not temperature-extrapolation support or a posterior confidence interval.

## Reuse

queries.json contains the exact challenge descriptions in fixed order. true_probabilities.npz contains query_ids (<U24), probabilities (120,64), and zero_field_probabilities (120,64).
Outcome bit k corresponds to readout[k], with bit 0=-1 and bit 1=+1. The field and beta conventions are identical to the live participant schema.
Saved model predictions use the same shape and ordering. per_query_scores.json and RESULTS.json include beta/family breakdowns and the twelve worst TV cases per model.
Only this response_stress directory was written. No fresh submission was inspected; no model was refitted. Parameters were opened only to generate exact labels after the query grid was frozen.

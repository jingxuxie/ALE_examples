# Quantum-memory failure predictor

Run the executable interface:

```sh
python solve.py TRAIN_CSV QUERY_CSV OUTPUT_CSV
```

`solve.py` is self-contained apart from the supplied NumPy and system SciPy.
It fits all parameters from the supplied training CSV at execution time.
`predictions.csv` contains its predictions for the 692 supplied queries.

## Method

- Fits Bernoulli count likelihoods for full-experiment failure probabilities, including zero-failure observations.
- Uses a saturating logical-error hazard, exponential distance scaling, regularized finite-size corrections, and noise-specific refinements.
- Blends two distance models and enforces monotonicity in physical noise.
- Extrapolates low noise with a nonnegative fault-order series blended with a locally fitted power law.
- Keeps honeycomb H/V observables separate; pools the symmetric surface X/Z observations within each decoder/style.
- Regularizes unresolved tails with a half-event probability floor derived from the largest training shot count.

## Validation

These are **training-only extrapolation tests**, not private evaluation scores.
Each split keeps observables and decoders of a physical configuration together.
Scores use the specified worst-family likelihood-support metric.

| Held-out training configurations | Submission | Starter |
| --- | ---: | ---: |
| Largest distance | 0.9105 | 0.8127 |
| Noise below 0.0005 | 0.9423 | 0.4173 |
| Noise below 0.0007 | 0.7732 | 0.4515 |
| Noise below 0.001 | 0.6287 | 0.4356 |

`validate.py` reproduces the tests when run from this directory with
`TASK_ROOT` pointing to the participant assets. Detailed results are in
`validation_results.json`.

The complete interface run took approximately 1.5 seconds and 63 MB peak RSS
under a 2 GiB address-space limit. Standalone dependency discovery, all 692
output IDs and probability bounds, query-order invariance, and the analytic
likelihood gradient were checked.

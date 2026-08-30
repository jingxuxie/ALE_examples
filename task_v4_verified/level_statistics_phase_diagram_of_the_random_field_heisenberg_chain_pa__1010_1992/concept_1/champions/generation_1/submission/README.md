# Fast sample-specific spin dynamics

The submission entry point is `predict.py`. Its only runtime assets are
`descriptors.py`, `fast_physics.py`, `model10.pkl.gz`, and `model12.pkl.gz`.
The two trained model files together occupy approximately 2.05 MiB.
Dependencies are the provided Python 3, NumPy, SciPy, and scikit-learn installation.

## Interface

Run `python3 predict.py` without arguments. After loading and warming the models
and the L10 spin sector, it prints and flushes `READY`. Send one JSON line with
`{"cases":[{"id":"example","L":10,"fields":[...]}]}`. It returns exactly one
JSON prediction per supplied ID and exits. No input-dependent work occurs before
readiness, and IDs are never model features.

The optional file interface is `python3 predict.py --input cases.jsonl --output predictions.json`.
Asset paths resolve relative to the script, not the working directory.

## Method

- Separate histogram gradient-boosting models predict L10 and L12 from 250
  shift-, reflection-, spin-inversion-, and common-field-offset-invariant ring
  descriptors. Each model has 550 boosting iterations and at most 31 leaves per tree.
- Training uses the 1,600 supplied training records plus 8,000 generated L10 and
  6,000 generated L12 records from the published sampling law. Generated training
  labels use single-precision dense diagonalization. Validation labels are not
  used for fitting; public validation is used for model selection.
- After surrogate prediction, a 1.25-second internal budget permits numerical
  corrections for L10 cases, prioritizing intermediate predicted fractions.
  This uses the full 252-dimensional zero-magnetization sector, periodic bonds,
  and the mean of the 84 middle-third eigenstate ratios. The solver uses single
  precision and preserves a valid surrogate result if its budget is exhausted
  or numerical diagonalization fails.
- The surrogate alone also passes both accuracy thresholds on public validation
  and the additional 1,600-case independent validation bank. Thus correctness
  does not depend on completing every numerical correction within the budget.

## Verification

`submission_report.json` records model hashes and the final results. All eight
recorded 320-case streaming runs pass both accuracy requirements and the runtime
limit with four-core affinity and a 2,048 MiB address-space limit.

| Check | Overall RMSE | Worst-family RMSE |
| --- | ---: | ---: |
| Public validation, surrogate only | 0.02391 | 0.02802 |
| Independent 1,600 cases, surrogate only | 0.02370 | 0.02956 |
| Independent 1,600 cases, timed hybrid | 0.01622 | 0.01810 |

The independent validation labels are recomputed in float64. Maximum measured
startup is 6.381 seconds; maximum complete inference, including process exit,
is 1.758 seconds. These are local constrained tests, not hidden-evaluator results.

Run `python3 test_stream.py --repeat 3` for the provided public validation,
`python3 test_interfaces.py` for schema, symmetry, immutability, and file-interface
checks, and `python3 test_physics.py` for comparison with the frozen physics.
The supplied `fresh_validation_0.jsonl` through `fresh_validation_4.jsonl` support
independent streaming tests via `test_stream.py --data <file>`.

## Reproduction

All development scripts run from this directory. The public inputs are read from
`../../participant/input` in the original task layout.

1. `python3 generate_data.py --count 6000`
2. `python3 generate_data.py --length 10 --count 8000 --seed 39723 --output generated10.jsonl`
3. `python3 train_models.py`
4. `python3 train_models.py --length 10 --generated generated10.jsonl --prefix candidate10`
5. `python3 package_models.py`

The training script records the compared models; packaging selects the compact
31-leaf histogram-boosting models. Independent validation uses generator seeds
549833 (L12) and 572891 (L10), 800 cases each, followed by `refine_validation.py`.

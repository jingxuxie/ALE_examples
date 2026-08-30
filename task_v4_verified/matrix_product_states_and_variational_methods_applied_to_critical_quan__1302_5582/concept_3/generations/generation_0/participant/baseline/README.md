# Runnable baseline

Uses only NumPy and labelled training cases. It fits a fixed kernel correction
to a low-cutoff gap anchor, separately for each chain length. No teacher calls,
private labels, private seeds, validation fitting, or hidden-set tuning are used.
Hyperparameters are fixed before the first evaluation. This is a smoke-test
reference, not a claimed passing model.

From `participant/`:

```text
OPENBLAS_NUM_THREADS=1 python baseline/predict.py --input input/validation_inputs.json --train input/train.json --output workspace/predictions.json
```

# Submission

The entry point is `predict.py`; it uses only `model.npz`,
`runtime_features.py`, `descriptors.py`, and system NumPy at inference.
Run it without arguments. It loads and warms the model, prints `READY`,
then reads one JSON line, returns one JSON prediction line, and exits.
No training data or target fields are read during startup.

## Method

The predictor uses translation-, reflection-, spin-flip-, and
uniform-field-shift-invariant statistics of the ordered fields. These
include disorder distributions, spatial correlations, resonant bonds,
local windows, transport spectra, and inexpensive single-particle
localization summaries at five hopping strengths. The single-particle
calculations are descriptors, not a replacement definition of the
interacting target observable.

Eight small, independently initialized neural regressors predict the
physical fraction. Training uses dropout, size-dependent sample weights,
and late-training weight averaging. Inference implements their fixed
weights directly with NumPy; PyTorch is not an inference dependency.

## Training and evaluation

`simulate.py` generates additional L14 labels with the supplied exact
Hamiltonian and middle-third eigenvector definition in `physics.py`.
The generator is the supplied `generators.py`. Simulation uses at most
eight workers, each with one numerical thread.

`train_final.py` trains on all 2,400 public records plus simulated records
320 through 1279. Simulated records 0 through 319 are excluded from
fitting. Records 1280 through 1599 form an additional, independent final
test set and are not used by the training script.

The final accuracy and protocol evidence is written to
`final_metrics.json`, `final_holdout.json`, and `final_runtime_repeat.json`.
These are local tests, not private evaluator results. The public L14
validation labels are included in the final fit; final accuracy claims
therefore use the independent simulated records rather than that public
split.

## Checks

`test_invariants.py` checks descriptor parity, physical symmetries,
uniform shifts, and empty/singleton inputs. `check_submission.py` launches
the actual streaming executable under a four-core affinity and a
2,048-MiB address-space limit. Its inference timing includes JSON input,
output, and process exit.

Re-run the final held-out protocol test with:

```
python3 check_submission.py --source simulated.jsonl --offset 1280 --count 320 --report final_holdout.json
```

Research scripts and logs are retained as implementation evidence; the
entry point does not import them.

# Interface

A request directory contains:

- `circuit.stim`: complete source-native noisy memory circuit.
- `model.dem`: `circuit.detector_error_model(decompose_errors=True)`, with correlation separators retained.
- `syndromes.npy`: uint8 array `(shots, num_detectors)` with values 0 or 1.
- `metadata.json`: noise family, geometry, number of measurement subrounds, observable, and physical error parameter.

Output must be a non-pickled `.npy` bool/uint8 array `(shots,)` or `(shots,1)` with only 0 and 1. A fresh process handles each request. `TASK_ROOT` points to the participant directory. The evaluator exposes only the current request, participant assets, and submission code; labels are never in the process filesystem allowlist.

Run the development baseline from the participant directory:

```
PYTHONPATH="$PWD/workspace" python baseline/solve.py input/dev_em3_h /tmp/predictions.npy
PYTHONPATH="$PWD/workspace" python workspace/check_development.py input/dev_em3_h /tmp/predictions.npy
```

`input/development_labels/CASE.npy` supplies labels only for development cases. The native model `EM3_v2` uses correlated measurement/data noise; `SD6` and `SI1000` use the paper's corresponding noisy gate sets. Evaluation uses widths 8–12, heights 12–18, subrounds 12–48, and physical error probabilities 0.0004–0.018 depending on family. The actual circuit, not the metadata alone, defines each distribution. Its single active observable is consistently reindexed as logical observable 0.

Core failure ratio is the mean of per-family total-error-count ratios to the fixed baseline. Worst-family ratio is their maximum. Passing requires core <=0.80, worst <=0.95, and pooled paired improvement exceeding three estimated standard errors. Baseline and submission use identical hidden shots. Invalid output or resource failure fails the run.

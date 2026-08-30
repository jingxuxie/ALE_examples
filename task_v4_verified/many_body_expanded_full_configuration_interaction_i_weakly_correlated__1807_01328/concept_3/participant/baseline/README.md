# Public baseline entry point

`run.py` executes the unchanged canonical baseline at `../input/workspace/baseline/predict.py`. It uses the canonical supplied datasets by default and works independently of the current directory.

From any directory, substitute the mounted participant path and a writable output directory:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B /path/to/participant/baseline/run.py --output /path/to/writable/output/predictions.npz --report /path/to/writable/output/baseline_report.json
```

`--output` is required. If `--report` is omitted, the report is written as `baseline_report.json` beside the predictions, never by default inside participant assets. Optional `--data` selects another compatible data directory. No model, selection rule, scientific target, or dataset is changed by this wrapper.

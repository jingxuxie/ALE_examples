# Public development interface

The participant task tree, including `baseline/` and `workspace/`, is read-only.
Use the writable `OUTPUT_DIR` supplied by the runner. From the participant root,
this example creates a self-contained baseline submission and development files:

```sh
: "${OUTPUT_DIR:?Use the writable directory supplied by the runner}"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 baseline/train.py --output-dir "$OUTPUT_DIR/submission"
python3 make_request.py input/validation.npz "$OUTPUT_DIR/dev"
python3 "$OUTPUT_DIR/submission/solver.py" "$OUTPUT_DIR/dev/request.json" "$OUTPUT_DIR/dev/predictions.json"
python3 score.py input/validation.npz "$OUTPUT_DIR/dev/predictions.json" --report "$OUTPUT_DIR/public_score.json"
```

`train.py` writes `solver.py`, `features.py`, `model.npz` and its training report to
the chosen destination; it does not modify any source asset. To use the supplied
fitted model without training, the equivalent submission consists of copies of
`baseline/solver.py`, `baseline/features.py` and `baseline/model.npz` together in
an output directory. Request/output paths need not reside in the submission.

The alternative native baseline uses `baseline_exact/solver.py`, `physics.py`
and `hubbard.so` together; its C++ source is also provided. It uses the same JSON
interface and supports both active sizes without editing dimension constants.
Neither provided baseline is asserted to satisfy all scoring conditions.

`make_request.py` removes `gaps`, writes the five input arrays to a new NPZ, and
creates a request with an absolute input filename. `score.py` reads the labelled
public archive and the saved prediction JSON. Its `passed` means accuracy only;
it does not certify memory, time or isolation. A submission directory must not
contain symlinks, hard links, private assets or special files.

Where the trusted evaluator is installed, the builder can run from the concept root:

```sh
python3 evaluator/evaluate.py "$OUTPUT_DIR/submission" --split validation --report "$OUTPUT_DIR/guarded_validation.json"
python3 evaluator/evaluate.py "$OUTPUT_DIR/submission" --report "$OUTPUT_DIR/hidden_report.json"
```

The second command is the final hidden evaluation interface, not a participant
label oracle. Every call runs a separate process. Exit code 0 means valid output,
not necessarily that accuracy passes; code 2 means invalid execution/output.
Detailed hidden labels and per-instance residuals are never returned.

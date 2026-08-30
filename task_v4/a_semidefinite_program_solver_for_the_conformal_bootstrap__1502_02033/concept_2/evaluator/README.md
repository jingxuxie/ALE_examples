# Private evaluation boundary

Deploy only `../participant/` to the solving agent. Keep this directory,
`../adversary/`, `../attempts/`, `../champions/`, and root metadata private.
Do not expose evaluator Python, its guard copy, or source-provenance notes as
participant assets. The public guard is intentionally identical to the private
target at freeze; exact evidence and hidden controls are independently written.

Run from concept_2 with a trusted interpreter/environment:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -I evaluator/evaluate.py participant/workspace/witness.json --output attempts/score.json
```

Or pass any absolute path to a submitted data file. Only that file is read as
submission data. Neither the submission directory nor public workspace is
added to `sys.path`. Private modules load by absolute path after SHA-256 checks
against the private frozen manifest. Deploy the entire evaluator read-only;
hashes detect accidental drift, not compromise of a mutable trust root.
The optional score destination is a harness-selected path, not submission data.

JSON scores always print; submission rejection is a scored outcome, not a
process error. Numerical and evaluator failures fail closed with zero success.
`valid` means admissibility, `evidence_valid` means a sufficient exact negative
quotient, and `passed` means both plus all three target profiles accepting.
For malformed data or insufficient evidence, profiles need not be executed.

Resource recommendation: one CPU, 256 MiB or more, 15 CPU seconds hard limit,
generous wall-clock allowance on the shared host. The measured normal workload
is recorded in `../adversary/control_report.json`; this task does not score host
wall time. All integer sizes, degree, dimension, and input bytes are bounded.

Private validation:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m pytest -q -p no:cacheprovider evaluator/test_hidden.py
python adversary/run_controls.py
```

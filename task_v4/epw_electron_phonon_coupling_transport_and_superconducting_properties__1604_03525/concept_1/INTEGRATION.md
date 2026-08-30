# Integration

The trusted evaluator uses the parent task's `authoring/sandbox.py` and its
`run_submission` API. Only submitted source and one observation archive are
mounted read-only; a fresh output directory is writable. Hidden spectra and
family labels are opened by the parent only after the isolated process exits.
Filesystem and network denial are independently audited in `authoring/`.

Run `python3 evaluator/evaluate.py --submission participant/baseline --output baseline.json`.
Add `--validation` for the public split. Inference has a 110-second wall timeout,
3 GiB address-space ceiling, and four-thread numerical ceiling. Overall scoring
must finish in 120 seconds. Missing isolation support is a failure, never an
excuse to execute submitted code without confinement.

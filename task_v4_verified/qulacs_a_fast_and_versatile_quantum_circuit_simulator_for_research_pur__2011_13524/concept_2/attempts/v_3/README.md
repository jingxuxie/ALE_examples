# Circuit witness submission

Run:

```sh
python solution.py INPUT_JSON OUTPUT_JSON
```

The executable reads `best_witness.json` relative to its own directory and
writes the required direct target-ID-to-gate-list JSON object. It needs only
Python's standard library at runtime and does not read participant files or
research artifacts. The two-qubit demo is also supported.

## Accuracy status

**The stated synthesis objective was not achieved.** The saved candidates are
legal and respect both gate budgets, but neither passes the required numerical
thresholds. `validation.json` records the public full-operator check, including
infidelity and phase-aligned Frobenius discrepancy. Do not interpret successful
execution or legal gate counts as a successful synthesis.

`validate.py` is the supplied public checker with a standalone command-line
entry point. Run `python validate.py INPUT_JSON OUTPUT_JSON` to reproduce the
metrics. Local development scripts and search artifacts are retained under
`research/`; they are not runtime dependencies.

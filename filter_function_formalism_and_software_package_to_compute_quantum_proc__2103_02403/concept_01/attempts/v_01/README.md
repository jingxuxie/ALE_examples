# Release-audited gate-sequence predictor

Run from any working directory:

```bash
bash /path/to/this/release/run.sh CASE_JSON DESTINATION --mode selected
```

Modes are `selected`, `baseline`, `refined`, and `no_memory`. Each invocation
writes `process.npz` (`channel`, `k2`) and `metrics.json`. The public conventions
are copied in `input/FORMAT.md`. No network access or original workspace path
is required. NumPy/SciPy and the auxiliary packages supplied for this task are
copied under `workspace/deps`; vendor licenses and metadata remain intact.

Start with `report.md` for the release decision and `workspace/METHODS.md` for
the mathematical methods, validity criteria and resource caveats. All tables
link to actual process artifacts. `claims.json` and `figures/sources.json`
identify the quantitative evidence. `iterations/` preserves superseded runs.

To reproduce the audit, run `bash workspace/audit.sh`. To run only the tests:
`bash workspace/python.sh workspace/validate.py validation/tests.json`.

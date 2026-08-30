# Trusted evaluator

Run from the concept root:

```bash
python evaluator/evaluate.py --submission participant/baseline --output report.json
python evaluator/evaluate.py --submission participant/baseline --output public_report.json --public
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python evaluator/test_system.py
```

The evaluator samples its own trusted simulator and imports no submission code. It launches a separate persistent Python process per episode, copies only the submission and public `input/` into a fresh directory, clears inherited environment variables, passes no hidden path in child arguments, and sends only public metadata and requested observations. Reports omit truths, seeds, and shot transcripts. Each private episode has independent parameter and outcome seeds. Invalid episodes score zero, remain in all aggregates, and prevent passing. The CLI still writes a structured report when a submission is absent or malformed; a failed score is not a shell failure.

## Integration security boundary

**The default runner is not a security sandbox.** Resource limits, fresh working directories, clean environment, and subprocess isolation do not prevent same-user filesystem or `/proc` access. Never treat an unwrapped, adversarial submission as isolated from `hidden/`. Only trusted authoring probes were used during calibration. Before fresh-agent evaluation, the parent must add its filesystem/process/network isolation and ensure hidden files are not mounted/readable, parent process memory is inaccessible, and child processes share an aggregate resource budget.

`--runner-prefix-json '["/absolute/path/to/isolating-runner"]'` prepends a trusted executable wrapper to `[python, -u, solution.py]`. The wrapper inherits the staged working directory and may bind only that directory plus required read-only Python libraries. It must not bind the repository or evaluator directory, and must preserve stdin/stdout, cwd, and the supplied command. This hook is for the trusted evaluation operator, not a submission-controlled option. No wrapper was asserted to be tested in this standalone concept. A bwrap wrapper can be supplied during parent integration; combine it with PID/network isolation and aggregate CPU/process limits as appropriate. The report distinguishes an external runner from the default resource-limits-only execution mode, but presence of a prefix does not certify the wrapper's security.

## Files and reproducibility

`hidden/episodes.json` is the immutable, balanced 18-episode private suite. `make_suite.py` created it once from entropy and refuses to overwrite it. The public examples are separate. Keep `hidden/`, the calibration reports, authoring provenance, and probe code out of the participant asset mount. Public assets are only `participant/`.

`config.json` holds fixed per-episode resource limits and target configuration. `test_system.py` checks an independent density-matrix derivation, analytic derivatives, physical bounds, exact aliasing on integer times and its resolution off-grid, correlation identifiability, score identities, and real subprocess rejection paths. It does not require a Qulacs install, a reference submission, network access, or regenerating hidden episodes.

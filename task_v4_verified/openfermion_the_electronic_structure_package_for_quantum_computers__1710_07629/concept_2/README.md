# Concept 2 — privileged builder package

**Distribute only `participant/`, read-only.** Everything else is builder/evaluator
private, including the generator, seeds, schedules, witness, freeze manifest,
validation fixtures, and reports. Main owns audit files, private launch metadata,
and fresh runner invocations; this builder neither edits those nor launches agents.

The submission is an artifact directory containing `solution.json`. Evaluate with
`python3 evaluator/evaluate.py SUBMISSION_DIR --report REPORT.json`.
No submission Python, pickle, NumPy object file, or shell command is executed.
The official evaluator imports no public simulator or submission module and reads
only its hash-checked private target copy. Thus its artifact checker does not need
a submission-code execution sandbox. Participant isolation is still mandatory to
protect the planted circuits; hiding directories by convention is not isolation.

Build environment: Python 3.10.12, NumPy 1.21.5, SciPy 1.8.0; OpenFermion absent
and not required. Participant development budget: one hour. No task runner changes.

The generator refuses to overwrite frozen targets. Reproduce it only in a clean
private copy without a freeze manifest, and compare target and witness hashes.
The committed targets, tolerances, and budgets must never change after fresh
attempts. See `PROVENANCE.md`, `evaluator/hidden/generation_diagnostics.json`,
`adversary/validation_report.json`, and `status.json` for build evidence.

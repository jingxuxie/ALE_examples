# Staged trusted evaluator

From the installed or staged root:

```
python3 -I evaluator/evaluate.py <submission_directory> --report <report.json>
```

A direct `design.json` path also works. The grader imports only its separately
frozen `validator.py`, verifies its checksum and the private target checksum,
and never imports participant code or submitted helpers. It uses native integer
pair products for all 4096 lags. Ordinary invalid artifacts return failure JSON;
configuration errors return exit two. The planted file is not needed for grading.

Authoring-only: `python3 -B evaluator/hidden/run_staging.py`. This command is for
the private staging layout, freezes once if necessary, audits exactness/security,
and generates the bounded baseline. It never launches agents. Do not run it
after moving the package without reviewing its active-generation guard paths.

Keep evaluator/, private staging, provenance, and readiness metadata outside all
participant allowlists. Same-user directory permissions are not sandbox isolation.

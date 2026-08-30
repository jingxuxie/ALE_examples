# Adversarial validation evidence

`evaluator/test_isolation.py` adapts the trusted reusable Landlock/seccomp tests
into this package. All temporary fixtures are created under this directory.
`evaluator/test_evaluator.py` validates malformed outputs and the evaluator boundary.
Reports are builder-only; neither submissions nor source labels are imported into
the trusted evaluator. Preserve the separately supplied main-agent canary/audit.

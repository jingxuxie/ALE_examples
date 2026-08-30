# Adversarial checker audits

Fixtures are created by `evaluator/audit.py` under this directory. Tests cover
duplicate keys, nonfinite controls, wrong schema, booleans, out-of-range depths,
zero/Clifford pulses, slew violations, oversized and missing artifacts, symlink
rejection, and malicious Python files that must never be imported.
These are evaluator-integrity tests, not additional hidden physics constraints.

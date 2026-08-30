# Robust false convergence under joint uncertainty

Find a counterexample experiment for the supplied nonlinear periodic-field workflow that survives **independently combined calibration, initial-shape, and phase perturbations**. The previous champion is supplied as the baseline, not as a passing solution. Submit only one admissible JSON experiment; do not replace the integrator.

The complete model, public finite perturbation design, numerical-reference checks, unchanged accuracy/diagnostic thresholds, scoring, schema, and resource budget are in `input/protocol.json`. Runnable simulation and screening APIs are in `workspace/`; `baseline/search.py` copies the previous champion. Every listed family member must satisfy the target.

This falsifies a claim about the supplied workflow, not a bug claim about XMDS2. Numerical uncertainty is estimated by refinement and an independent method, not treated as a rigorous PDE bound.

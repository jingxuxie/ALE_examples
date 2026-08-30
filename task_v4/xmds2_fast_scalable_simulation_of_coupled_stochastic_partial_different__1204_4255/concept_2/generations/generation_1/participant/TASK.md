# Robust false convergence in a nonlinear periodic field

Find a **counterexample**, not a replacement integrator: submit one admissible smooth two-component initial-value experiment for the supplied nonlinear simulator. Its coarse/fine temporal certificate must pass, while independently refined references show a substantial error in physically observable low-wave-number densities. The discrepancy must persist across all public nearby perturbations and three observation times, with conservation and spectral-tail diagnostics within their limits.

The complete model, parameter bounds, submission schema, family, numerical checks, resource budget, scoring rule, and exact target are in `input/protocol.json`. The runnable simulator and search API are in `workspace/`; `baseline/search.py` produces a weak starting submission. Only your JSON witness is graded. Do not alter the evaluator or submit executable code.

This challenges a supplied numerical workflow, not the correctness of XMDS2. No claimed estimate is treated as a rigorous error bound.

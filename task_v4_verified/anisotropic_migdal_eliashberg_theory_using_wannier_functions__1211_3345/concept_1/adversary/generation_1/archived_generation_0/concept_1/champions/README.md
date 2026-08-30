# Privileged attainability witness

Offline branch construction and reference evidence belong here. This directory
must not be mounted in a participant's environment. An offline witness is not
automatically evidence of meeting the participant's compute budget.

## Completed evidence

`build_references.py` constructs each branch from two independent starting
amplitudes with the builder-owned fast operator. It certifies the result using
independent blocked direct sums. All 20 cases pass. The largest gap-equation
residual across both starts is 1.036e-13 and largest relative two-start branch
disagreement is 6.583e-11. Per-case JSON/NPZ evidence is stored privately under
`../evaluator/hidden/references/`. No infinite-cutoff or thermodynamic-uniqueness
claim is made.

`solve.py` and `solver_core.py` constitute the fixture-free executable witness.
The solver uses only the public instance, public operator/JVP, and NumPy/SciPy.
It has no case IDs, hidden parameters, reference tables, or private-file reads.
Private branch construction and same-budget execution are separate measurements.

The final sealed-evaluator run in `../attempts/champion_report.json` passes 20/20,
core score 1.00, worst-family score 1.00, and all mode-A improvement gates. It
uses 30.787 total child CPU seconds, maximum 5.331 per case against the exact
12-second budget. End-to-end evaluation takes 63.55 seconds on this run. The
child uses the shared Landlock/seccomp runner plus the local clone/clone3 guard.

This establishes joint numerical quality and resource attainability, not task
difficulty against a fresh participant. The parent owns fresh-agent trials.

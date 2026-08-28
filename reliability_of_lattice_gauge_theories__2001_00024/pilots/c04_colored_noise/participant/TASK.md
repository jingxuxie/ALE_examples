# Calibrate and protect a noisy gauge simulator

Implement root `solver.py` with `solve(case: dict) -> dict`.

Infer the colored, spatially correlated bath from calibration measurements;
compute frequency-resolved dissipative responses; predict the protected dynamics;
and choose a realizable setting within the actuator budget. Preserve the intended
dynamics, not merely a small gauge violation.

The complete model, JSON contract, tolerances, resource limits, and scoring are in
`input/protocol.md`. `input/example_case.json` is one unlabeled interface example.
Return only JSON-serializable finite values. NumPy and SciPy are available.
Do not access private files, other submissions, or the network.

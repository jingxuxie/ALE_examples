# Calibrated many-body reliability

Deliver `solver.py` with `solve(case) -> dict`. Infer the device's coherent faults
from its calibration traces, then predict the requested gauge-resolved dynamics
and connected correlations on the supplied chain. The input contract is in
`input/protocol.md`; `workspace/dense_cluster.py` is a small-cluster starting point.

Return all numerical predictions, not a narrative. Evaluation covers calibration,
gauge leakage, matter dynamics, spatial correlations, and family shifts under a
3600-second, 6-GiB per-case evaluation budget. Do not replace the requested chain by an
unjustified small-system extrapolation. Write your submission into the attempt
directory supplied by the runner; NumPy and SciPy are available.

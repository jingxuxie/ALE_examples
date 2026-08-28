# C01 empirical compression audit

Initial requested-model run: `runs/c01_correlated_tomography/screening/result.json`.
It exits normally after 623.48 seconds, with an unchanged public tree and a
complete root `solver.py`. This is not a timeout or missing-artifact failure.

Actual isolated screening and challenge results both have mean=1.000 and
worst-family=1.000. All four families and both scored components achieve 1.000.
The 12 screening cases and four private challenge cases cover missing correlated
channels, different support assumptions, and the contaminant/leakage extension.

The submitted implementation is generic: `attempt/solver.py` defines a weighted
two-column fit, constructs measurement envelopes, minimizes required envelope
inflation, and solves endpoint linear programs with feasible witnesses. It uses
SciPy's general LP solver rather than case identifiers or expected-answer tables.
No private reference is passed to `solve`: the evaluator passes only `entry["case"]`.

The public contract reduces all permitted real-data instances to the same
well-posed linear-fit and LP procedure. These are two numerical components, so
the preliminary anti-compression gate justified an empirical pilot, but they are
not independently difficult after the contract is formalized. The actual source
data and challenge results establish robust solvability, not frontier hardness.

No meaningful source-grounded failure region has been found within this contract.
Changing to unobserved true populations would introduce missing ground truth;
making the LP ill-conditioned or renaming identifiers would manufacture a trap.
Disposition: reject as robustly solved. Do not spend a ratchet on tighter
tolerances, more rows, or hidden detector assumptions.

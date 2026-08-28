# Correlated double-well tomography

Reconstruct occupation-sensitive oscillation amplitudes and certify the sharp
range of local gauge-invariant populations consistent with imperfect readout.
Respect positivity, measurement uncertainty, and incomplete identifiability;
do not replace correlated occupations by products of marginals.

Implement `solver.py` exposing `solve(case: dict) -> dict` in your submission
directory. The complete numerical contract is in `input/protocol.md`; the single
unlabeled example illustrates the schema. Use `workspace/` for scratch work.
Both readout fitting and population certification are scored numerically.

# Self-consistent gate-set noise calibration

Build a reusable, single-file `solver.py` that learns from finite-shot Clifford experiments with unknown local Pauli gate noise and unknown preparation/measurement noise.

For the supplied noise queries, distinguish structural identifiability from identifiability under the available calibration designs. Estimate supported query values and predict the signed parity means of held-out circuits. Do not replace unidentifiable quantities with claims about an arbitrary fitted gauge.

Run as `python solver.py INPUT.npz OUTPUT.npz`. The physical conventions, complete numeric schema, output arrays, scoring and resource limits are in `input/FORMAT.md`. Use NumPy/SciPy and the standard library; the evaluator stages only `solver.py` and one hidden input per fresh process.

Identification, invariant estimation and held-out prediction are independently scored across local gates, parallel crosstalk and incomplete-calibration regimes. Optimize accuracy across families, not just the example. `input/example.npz` is one small unlabeled example; develop in `workspace/`.

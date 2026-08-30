# Active detector-channel calibration

Build a standalone Python program that learns positive fault-channel rates from
syndrome observations while choosing how to spend **40,000 experimental shots**.
You have **one hour of coding time**. Submit `solution.py` in your designated
writable submission directory; use `/usr/bin/python3` with NumPy/SciPy.

This is a **synthetic controlled inverse problem**, motivated by calibrating
detector error models for matching-based decoders. It is not a hardware simulator,
a reproduction of either paper's experiments, or a test of decoder speed.

Each episode gives you detector footprints, allowed intervention configurations,
known exposure/mixing coefficients, and rate bounds. Unknown stationary rates
generate overlapping graphlike and higher-order detector faults. Some channels
share a reference footprint and become distinguishable only under interventions.
An unobserved shared shot mode and alternative footprints make inference nonlinear.
Neither individual faults, shot modes, hidden rates, nor hidden episode seeds are
observable. Choose configurations and shot allocations from previous observations;
then return one positive rate per channel. There are three structural regimes:
`chain_hooks`, `patch_crosstalk`, and `burst_aliases`.

Your objective is accurate recovery across **all four channel families**, not just
common faults. The official loss pools squared natural-log rate errors within
each regime/family, takes the square root in each of the 12 cells, then reports
their equal-weight mean and maximum. **Both frozen thresholds in
`input/targets.json` must pass**, with valid protocol and resource use on every
episode. All methods, including nonadaptive methods, are allowed; adaptive
experimental design is the intended route to better accuracy.

Read `input/API.md` for the complete model and JSON-lines contract. Run
`input/local.py` against the disclosed training episodes. The runnable
`baseline/uniform_ml.py` spends shots uniformly and fits the full likelihood;
it is a starting point, not a guaranteed passing solution. `input/model.py`
provides optional analytic likelihood, derivatives, and fitting utilities.

The scientific motivation is Sparse Blossom, arXiv:2303.15933, sections 2.1–2.3
(known error priors and graphlike models), and Takou–Brown, arXiv:2504.20212,
sections II.1–II.2 (syndrome-only estimation and higher-order correlations).
No PyMatching, Stim, scikit-learn, Torch, or network access is required.

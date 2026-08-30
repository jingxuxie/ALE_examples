# Fully family-calibrated mirror-benchmark falsification

Audit a quantitative robustness claim for mirror randomized benchmarking:
within the supplied calibrated Markovian noise class, a near-exponential
mirror decay cannot underestimate the true layer infidelity by 2.35% or more.
Produce a counterexample, not a critique of the paper's general theorem.

The assets specify a four-qubit Clifford ensemble, a runnable baseline, exact
noise-channel constraints, and a deterministic public checker. All layers must
retain 2% infidelity and match both the baseline average error channel and its
depth-two mirror polarization separately within the one-qubit and CNOT layer
families, as well as in their fixed mixture.
Only the integer noise allocation is under your control.

Write `witness.json` in your output directory, with the schema in
`input/MODEL.md`. Check it with `python workspace/check.py PATH/witness.json`.
The baseline runs as `python baseline/solve.py --output PATH/witness.json`.

A valid witness satisfies every exact calibration constraint, relative fitted
infidelity bias at least 0.0235, maximum polarization fit residual at most 0.004,
and depth-256 polarization at least 0.005. The checker reports bias and validity;
approximate calibration matches do not count. The artifact limit is 64 KiB.
You have one hour, CPU-only local computation, and no external data or network.

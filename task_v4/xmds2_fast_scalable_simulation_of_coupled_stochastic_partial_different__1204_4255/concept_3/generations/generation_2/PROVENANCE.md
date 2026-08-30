# Ratchet 1: verified joint-uncertainty coverage

This is generation 2 of concept_3, not a fourth concept. Generation 1 is solved:
both canonical original fresh controls pass its frozen evaluator. The selected
champion is the original `attempts/v_2/control.json`, copied byte-for-byte into
`champions/generation_1/control.json` and this stage's `participant/baseline/control.json`.
The organizer champion provenance includes its cutoff-record hash and timestamp.

## What changes and what does not

Only evaluation coverage and read-only-safe public smoke I/O change. Equations,
2D domain, T=8, target-state rule, full eight-dimensional uncertainty box, all
control amplitude/slew/acceleration/RF bounds, all numerical audit limits, and
the .990/.985/.980 thresholds remain identical. The trusted solver and evaluator
source bytes are unchanged. The score still equally weights five families.
All 21 legacy cases remain, with four new public examples and twelve focused
held-out joint cases: 37 total, family counts 9/4/4/4/16.

## Broad evidence and independent certification

The sampler was fixed before its runs: all 256 corners and 64 Latin-hypercube
interiors, seed 2026082801. A new 64x32, dt=.02 screen checked all 320 cases.
It found 71 raw-fidelity failures below .98
(71 corners, 0 interiors),
with minimum 0.953861799. These coarse numbers were leads,
not passing/failing proof. Original fresh stress files were consulted only as
scientific leads; no fresh-agent score was accepted as certification.

Independently regenerated stationary references and the trusted A/B/C integration
checked 26 selected cases. Of these,
24 were numerically certified fidelity
failures and 0 failed a numerical guard.
No numerically invalid or reference-uncertain case was selected for the stage.
Reference residuals in this check reached at most 8.41e-07.

Strong failures and the largest boundary-tail leads also received a 160x80,
dt=.0025 independent grid/time refinement:

| Case | Extra-refined fidelity | Difference from C | State distance | Boundary mass |
| --- | --- | --- | --- | --- |
| corner_248 | 0.953859757 | 9.45e-08 | 4.83e-06 | 6.7e-10 |
| corner_249 | 0.957098230 | 2.73e-07 | 4.74e-06 | 1.16e-09 |
| corner_240 | 0.957609466 | 2.08e-08 | 5.25e-06 | 8.93e-10 |
| corner_207 | 0.991924233 | 2.01e-07 | 7.5e-06 | 2.43e-09 |
| corner_205 | 0.989756847 | 2.94e-07 | 5.95e-06 | 2.13e-09 |

These extra checks separate spatial/temporal error from resolved probability
in the boundary guard. Boundary mass uses a hard region indicator, so its finite
grid quadrature can vary even when the complete complex field converges. A
boundary excursion is not counted as a fidelity failure. Such leads are retained
in the organizer evidence and excluded if they fail any prescribed audit.

## Failure clusters

Four normalized-parameter farthest-first anchors partition the strongest safe,
certified failures. The anchors become public examples; twelve additional
low-fidelity cases become held-out coverage. Diagnostic bounding ranges appear
in `participant/input/focus_regions.json`; they do not replace or narrow the
original Cartesian box. Exact membership and source-case IDs are recorded in
the organizer's `adversary/ratchet_1/selection.json`.

Across the full 256-corner screen, the following conditional means describe
associations, not a causal decomposition:

| Parameter | Low-end mean | High-end mean | Low/high counts below .98 |
| --- | --- | --- | --- |
| g | 0.982488 | 0.985818 | 47 / 24 |
| bias | 0.982874 | 0.985432 | 43 / 28 |
| rf_gain | 0.982896 | 0.985410 | 39 / 32 |
| cross_ratio | 0.984763 | 0.983543 | 37 / 34 |
| trap_x | 0.984389 | 0.983917 | 36 / 35 |
| self_ratio | 0.984060 | 0.984246 | 33 / 38 |
| trap_y | 0.984067 | 0.984239 | 37 / 34 |
| gradient | 0.984197 | 0.984110 | 40 / 31 |

## Certified champion baseline on this stage

The original champion is **valid, but fails fidelity**, with audited core
0.9895733197, weakest-family mean 0.9709376199
and weakest-case fidelity 0.9538570747.
Maximum fidelity allowance is 1.39e-05; maximum
stationary reference residual is 1.11e-06.
The full frozen stage report is `attempts/baseline_evaluation.json`.

No new fresh agent or private optimizer was run. Generation-2 solvability is
unknown; failure of this champion is not evidence of impossibility or final
hardness. Stage assets and target/case hashes are frozen before the next trials.

## Scientific seed

The XMDS2 paper arXiv:1204.4255, original GrahamDennis/xpdeint examples and XMDS
Fourier/IP documentation remain the source connection. See the retained primary
source list in `participant/input/SOURCES.md`. This independent NumPy/SciPy GP
split solver is not claimed to be XMDS-generated code. The ratchet strengthens
coverage of the same atom-optical control artifact, not the physical model.

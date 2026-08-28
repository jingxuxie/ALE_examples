# Valid initial tournament: method and outcome audit

Only the four completed runs in this directory count. The separately archived prematurely interrupted runs are not scored, not mined for counterexamples, and not available to these fresh agents. See `authoring/launch_audit.md` for that parent orchestration error.

## 01 — Covariant pipeline: solved

The submitted implementation repairs actual Cartesian-centre and metric-nearest-atom handling, preserves Wigner–Seitz hopping corrections, and transports full complex Hamiltonians through unit-cell changes and supercells. It checks full matrices, not merely sorted eigenvalues. It also ran its own independent sums, folding checks and randomized transport checks. The valid fresh run completed in 937.47 seconds. Test and challenge scores are indistinguishable from one in all three families.

This is a real repository solution gap but not a frontier-hard gap for the requested model. The generic shortcuts proposed in the candidate ledger (dropping wsvec, fractional Euclidean distance, comparing bands only) would be wrong; the agent instead implemented the missing capability correctly. No substantive failure region was observed in the source-grounded pool. Contrived floating-point coordinate extremes or unrelated larger tasks are not added to rescue it.

Evidence: `pilots/01_covariant_pipeline/attempt/`, its complete terminal log, the test/challenge score reports, and the official-source validation report.

## 04 — Effective physics: solved

The submitted implementation uses real-linear unitary/antiunitary intertwiner recovery, polar-unitary correction, a canonical wave-operator expansion through cubic order, and the orbital plus spin Zeeman contribution. It uses all 600–800 input bands. The valid fresh run completed in 842.39 seconds. All four test material families and all six challenge families, including separately retained complete Bi2Se3 doublets, score approximately one.

This is not a band-only or projected-spin shortcut. The general implementation genuinely covers the separately scored physics. The submitted code is much cheaper than the official author reference's large intermediate arrays, and shows no meaningful runtime bottleneck in the tested regime. Exact retained/excluded degeneracy is outside the well-defined reduction and fails the reference too; it is not a legitimate counterexample. No additional synthetic singularity or new physical task is introduced to manufacture difficulty.

Evidence: `pilots/04_effective_physics/attempt/solve.py`, the claimed limitations in its README, all matrix-valued source-reference scores, and `authoring/pilot04_independent_validation.json` (fourth-order finite-q remainder and agreement with published magnetic coefficients).

## 02 — Operator response: residual is not acceptable hardness

The valid run completed in 818.45 seconds. Initial Te performance is 0.860326; the Te challenge is 0.849964, while magnetic Fe is solved. The source-guided audit demonstrates real changes in Berry/optical predictions, not a harmless common-origin gauge difference. Nevertheless, the residual comes from an under-specified choice of repair map: projecting the complete position operator versus separately projecting its stored connection and centers. Matching the source's particular convention raises the existing implementation to approximately 0.997 without changing its response algorithm.

That observation cannot be used as evidence of an unsolved frontier component. It violates the requirement that the public task completely specify its central outcome. No second independent failure remains after resolving this convention. The concept is rejected rather than strengthened by hiding this rule or concentrating weights on it. Detailed counterfactuals, gauge controls and source reexecution are in `authoring/pilot02_ratchet.md` and its private audit records. No ratchet was built for this invalid failure region.

## 03 — Device transport: initially solved; final scale search

All test and challenge families are solved to approximately one, including real full-hopping Si/InAs devices, two/three terminals, singular lead hopping and channel/noise outputs. The submitted implementation fits the public resource limits comfortably. Small differences around 1e-10 in scores are numerical roundoff, not meaningful hardness rankings.

This is provisionally the second concept considered for the counterexample stage because realistic rank-deficient lead scaling is a source-grounded remaining direction. A bounded private search tests larger physically equivalent principal-layer groupings, accepting only cases where the official reference succeeds under the same limits. Its outcome is recorded separately in `authoring/pilot03_counterexamples.md`. If no such region exists, the concept must be rejected; the successful initial solver is not evidence for a hard task.

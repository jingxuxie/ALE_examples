# Privileged search ledger (not participant material)

The presearch hashes lock the actual adaptive integrator, admissible witness
domain and public kernel. They are checked again during packaging. No target
or domain changes were made in response to unsuccessful searches. No agents
were launched by this builder; the main orchestrator owns the two fresh runs.

## Search sequence

1. `search.py`: global near-nullspace and linear-program screens attempt to
   cancel all eight fine-panel embedded defects and four coarse/fine defects
   in all three colors. There are 36 joint constraints on 24 coefficients.
   This search failed: its best observed errors were ordinary floating noise,
   many orders below the fixed success condition. Full outcomes are in
   `search_outcomes.json`; improvements are in `search.log`.
2. `search_localized.py`: cancel the defects of a single sibling pair and its
   parent comparison, letting the genuine adaptive algorithm refine the rest.
   This produces real underestimation but fails the fixed materiality gate.
   The independently graded best core/worst scores were
   0.0169375453302255 / 0.015458543201069127, with direct native confirmation.
   `localized_search.log` records the improvement sequence. The final bulk
   ledger write hit the OS command-argument size limit; this authoring-only
   writer was fixed to pass patches through stdin. It is not an integrator bug
   and no witness was accepted because of it. Rerunning the script reproduces
   the deterministic search and now writes its complete ledger.
3. `search_single_leaf.py`: target one leaf's own missed integral, rather than
   the total error of the initial uniform grid, and allow the sibling to be
   repaired by ordinary adaptive refinement. Six joint color constraints
   preserve one falsely converged leaf while the remaining mesh adapts.
   The independently graded best core/worst scores were
   0.36725966247616365 / 0.36596493094725413, still not a full counterexample.
   The two direct native computations agree and corroborate the surrogate.
   Full screens are in `single_leaf_search_outcomes.json`.
4. `search_l1.py`: optimize material missed error per integrated absolute
   moment, rather than raw error alone. This uses a constrained linear program
   on a 512-point diagnostic grid, followed by honest adaptive integration,
   coefficient-lattice validation and independent grading. The grid is only
   an optimization aid; it is never a grading reference. Its complete outcome
   is in `l1_search_outcomes.json` and its official selected-witness grade in
   `best_screen/report.json`.

`package_results.py` promotes a witness only when the official evaluator
passes all families and `verify_native.py` independently confirms that same
JSON. Otherwise it retains the best attempt and reports achievability as
unknown. Merely obtaining a large screen error or a positive partial score
does not establish a successful counterexample.

## Interpretation and limitations

This is correlated quadrature-error construction for genuine signed EEC
moments, not a claim that raw formula cancellation causes the failure. The
same stable function is integrated by target and independently refined grids.
The method uses a fixed finite Fourier band; no discontinuity, unbounded
frequency, adjustable narrow feature, or node-interpolating function is added.
The native and surrogate discrepancies are separately measured and subtracted.

When available, `robustness_diagnostics.json` records how the weight's energy
is distributed over all four quarters, adjacent lattice-point screens, and
ordinary single-mode controls at the same high frequencies. These diagnostics
are not separately native-certified witnesses. Baseline failures alone are
not evidence of scientific or fresh-agent difficulty. An expert white-box
inverse-design method is permitted by the task; this is not a secrecy-based
benchmark or a claim that the mechanism is unique to EEC.

## Engineering notes

An initial source-table export also exceeded the shell argument-size limit.
It was fixed by passing `apply_patch` through stdin and the complete source
calibration was regenerated. The final calibration, manifest, tests and
grades all use the successful export. The public kernel hash reproduced the
presearch hash exactly. Original paper files and the source-native oracle
remain outside `participant/`.

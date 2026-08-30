# Hardness discovery — p†q (2106.06850)

## Concepts and verification modes built

- **concept_1 — A, baseline improvement:** memory-bounded joint contraction planning for source-native CC, response, and density batches.
- **concept_2 — B, counterexample/falsification:** a physically constrained, ground-connected CCSD lambda-density population counterexample, ultimately checked at 243 coordinate and adaptive perturbations.
- **concept_3 — C, witness construction:** compact spin-preserving fermionic excitation circuits for complete correlated target states, under 24/28/32-gate caps.

## Baseline and champion scores

- **A:** baseline 1.0; privileged portfolio 1.291981598 overall, worst family 1.021440250. Fixed target was 1.75 overall and 1.15 in every family.
- **B:** random baseline 0 in every generation. Best fresh witness cores in generations 1–3 were 0.050007892, 0.607015128, and 0.039804144. Both generation-three champions score 0 under the final adaptive rule. The fixed population target remains 0.02.
- **C:** original baseline 0.857503373; original champion 1.0. Ratcheted baseline 0.773572868; bounded transferred-champion worst fidelity 0.837040770. Private exact circuits score 1.0 on every final case. The fixed target is 0.999999999 in every case.

## Fresh-agent scores

Every session uses isolated, read-only participant assets, an initially empty output directory, ultima-alpha, and a 3,600-second limit. Public-file hashes and allowlist settings pass the 14-session audit.

| Concept | Generation | Replicate core scores | Decision |
|---|---:|---|---|
| concept_1 | 1 | 1.291981598 / 1.291749551 | invalid target; cancelled |
| concept_2 | 1 | 0.03001241699 / 0.05000789168 | solved |
| concept_2 | 2 | 0.6070151283 / 0.1563409517 | solved |
| concept_2 | 3 | 0.03980414383 / 0.02300003356 | solved |
| concept_2 | 4 | 0.005577811055 / 0.008296456804 | hard_open_candidate |
| concept_3 | 1 | 1 / 1 | solved |
| concept_3 | 2 | 0.9562639168 / 0.9490407967 | hard_verified_achievable |

A's two sessions were generator-cancelled only after the frozen target was proved infeasible; their checkpoint scores do not establish hardness. Both final C sessions used the full hour, produced structurally valid capped circuits, and failed all three fidelity targets. Detailed scores and runtime records are in `authoring/score_ledger.json`.

## Counterexample search results

- **A:** an exact universal certificate bounds response-family speedup by 1.022753055829, below the required 1.15. Independent integer-certificate rechecking passes. This concept is invalid, not hard.
- **B, first ratchet:** the original witnesses have DAD 0.277948 and 0.382145, exposing the density-asymmetry blind spot.
- **B, second ratchet:** valid integral perturbations expose 266/384 and 165/384 DAD failures in the two quiet-density champions; the public 241-point coordinate stencil independently reproduces genuine accuracy/asymmetry failures.
- **B, final ratchet:** the two coordinate-robust champions pass 512 and 256 isotropic probes, respectively, but fail both same-radius adaptive energy-gradient probes. Maximum energy errors are 0.0003411934 and 0.0002345538 against 0.0001; the latter also violates DAD. No invalid-domain probe is counted as physics evidence.
- **B, private feasibility search:** 310 relaxation starts and stationary/finite-probe portfolios yield seven independently scored artifacts and 1,701 endpoint checks, but no passing witness. A rational exclusion applies to only one relaxed tuple, not the task; no universal impossibility result is claimed.
- **C:** 18 certified, dense/full-rank private cases defeat bounded 60-second champion probes. Three selected cases still fail after additional 300-second probes. Extended old-control reproduction is partial (2/3), so no full-hour transferred-champion failure is claimed. The two new independent full-hour attempts supply the hardness evidence.

## Ratchet generations

- A: **0**; B: **3**; C: **1**. Three concepts and three distinct primary modes were built.

## Final status and solvability

- **Selected: concept_3 — hard_verified_achievable.** Solvability is demonstrated by private circuits, a separate Jordan–Wigner/dense-exponential audit, and main-session certificate rechecking. Fresh worst fidelities are 0.9562639168 and 0.9490407967.
- **concept_2 — hard_open_candidate.** Final fresh cores: 0.005577811055 / 0.008296456804. Solvability: unknown_no_passing_witness_or_infeasibility_proof. The trusted numerical, gradient, parser, and 243-path zero-example audits pass.
- **concept_1 — invalid.** The improvement target is disproved under its frozen interface; cancellation and nonpassing scores are excluded from hardness evidence.

## Substantive capability failures

- **C:** joint discovery of a compact noncommuting excitation sequence and its angles when sparse support and Schmidt-rank reduction no longer identify reverse steps. Fast compiled simulation, topology search, angle refinement, structured ansätze, and reverse synthesis improved the baseline but remained substantially below the certified target.
- **B:** simultaneous stationary-CCSD witness construction and worst-direction robustness, not merely accurate energy or coordinate-wise screening. Final evaluator diagnostics distinguish physical constraints from malformed artifacts.

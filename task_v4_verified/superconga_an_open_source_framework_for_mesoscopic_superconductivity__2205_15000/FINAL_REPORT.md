# Final hardness report

## Concepts and scores

Three concepts were built in modes **A, C, E**. The GL and BdG models are declared
mesoscopic superconductivity surrogates, not reproductions of native SuperConga.
All score pairs are **core / worst family or operating condition**.

| Concept / mode | Task generation | Baseline | Private feasible solver/design or champion | Fresh ultima-alpha | Decision |
| --- | ---: | --- | --- | --- | --- |
| GL optimization — A | 1 | 0.0000 / 0.0000 | 0.7868 / 0.5677 | 0.9858 / 0.9573 | solved |
| GL optimization — A | 2 | 0.0000 / 0.0000 | 1.0000 / 1.0000 | 1.0000 / 1.0000 | solved |
| BdG inclusion design — C | 1 | 0.1765 / 0.1446 | 1.0000 / 1.0000 | 1.0000 / 1.0000 | solved |
| BdG inclusion design — C | 2 | 0.0000 / 0.0000 | 1.0000 / 1.0000 | 1.0000 / 1.0000; 1.0000 / 1.0000 | solved |
| BdG inclusion design — C | 3 | 0.1359 / 0.1090 | 1.0000 / 1.0000 | 0.5736 / 0.5196; 0.5604 / 0.5314 | hard_verified_achievable |
| LDOS active tomography — E | 1 | 0.6667 / 0.5000 | 1.0000 / 1.0000 | 1.0000 / 1.0000 | solved |

The fixed targets are GL **0.65 / 0.45**, spectral design **0.96 / 0.94**,
and tomography **0.70 / 0.50** plus its reconstruction-quality gates.
Eight isolated, ephemeral fresh sessions received participant-only access and
initially empty outputs, each with a 3600-second limit. All exited normally.
The two final spectral trials used 3586.70 and 3534.77 seconds; both artifacts
were fabrication-valid and written before their deadlines.

The final GL champion takes 36.39–56.89 seconds per case, below 60 seconds.
Tomography's corrected champion has mean CPU 14.28 seconds and maximum 48.26,
below 90 seconds; correcting process-tree CPU accounting did not change its
perfect quality score. The retained spectral witness verifies in under one second.

## Counterexample search

- **GL:** the first 24-case sweep isolated six persistent collective-winding
  gaps; three became generation 2. The old champion's two warm core scores were
  0.0688 and approximately zero. The new fresh solver scores 1/1. A subsequent
  bounded 13-case replay from a preserved 24-case corpus used 21 solver launches:
  eight cases closed their gaps, two showed stationary vortex-pinning gaps,
  and three hit resource deadlines. The declared repeat-load qualification
  was inconclusive. The two pinning regressions nevertheless survive six normal
  repeats with ample unused budget, so time truncation does not explain them.
  Previously recorded generation-1 champion fields close 0.9539 and 0.7981 of
  these gaps, leaving only 0.0554 and 0.1103 energy units. This is previously
  demonstrated capability, not a promising novel hard target. Historical initial
  arrays differ, so no new exact-input runtime qualification is claimed.
  No third generation was installed, and no broad-robustness claim is made.
- **Spectral:** the first ratchet screened 15 physical cases in 62 runs;
  the selected old-champion score was 0.0700/0.0586, but both new fresh agents
  solved generation 2. The second ratchet screened 19 cases including controls.
  Its full-strength selected-case replay completed 48 six-stage continuation
  seeds plus 24 auxiliary fits: 71,948 function evaluations and 60,341 CPU-seconds,
  with no pass. Best fabrication-valid champion score was 0.2942/0.2812.
  The generation-2 control still solved; matched smaller-island and fourfold
  spectral-grid refinement controls supported a genuine inverse-design gap.
  One incomplete large-geometry screen was not counted as a failed run.
- **Tomography:** 183 isolated review episodes included a 96-case broad sweep
  with 91 successes. Candidate failures did not survive unchanged replay;
  reduced-query controls also failed to establish a harder generation.

## Ratchet generations

Installed ratchets: **GL 1; spectral 2; tomography 0**.
Corresponding task generations: **2, 3, 1**. No concept exceeds the generation cap.

## Final status and solvability

**Retain `concept_2` as `hard_verified_achievable`.** Its private fabrication-feasible
design independently scores essentially 1/1, while two fresh one-hour attempts
remain at 0.5736/0.5196 and 0.5604/0.5314 against 0.96/0.94 targets.
Solvability is **demonstrated**, not unknown. GL and tomography remain **solved**
on their frozen official tasks; broader inconclusive searches do not change that.

## Substantive failed capability

Global binary inverse spectral design: recovering a connected-superconductor,
exact-material-budget pattern whose interacting inclusion resonances reproduce
all three public fingerprints. The failures are large spectral errors, not
missing files, hidden trivia, malformed artifacts, or infrastructure timeouts.
This is empirical one-hour hardness, not an impossibility or complexity proof.

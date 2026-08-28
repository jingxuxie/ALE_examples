# Reliability of lattice gauge theories: task-mining tournament

Status: **complete — all four tested concepts rejected; no production task accepted**.

Authoring began 2026-08-27 America/Los_Angeles (2026-08-28 UTC).
Target: arXiv:2001.00024v1 / PRL 125, 030503 (2020).
Fresh model: the requested `ultima-alpha`, high reasoning effort, at most 3600
wall seconds per attempt. Later confirmation runs, if justified, use independent
fresh sessions of this same requested model, not a claimed different architecture.

## Candidate directions and artifact evidence

The full eight-direction register is `authoring/CANDIDATES.md`. It records the
starting artifact, privileged artifact, outcome, likely shortcut, failure regime,
independent bottlenecks and verification for every candidate:

| Direction | Capability gap | Initial disposition |
| --- | --- | --- |
| A | Degenerate joint-sector diagonalization before/after QuTiP #2586 | Verified downstream patch; not built |
| B | Full penalties to bounded single-body/pseudogenerator control | Built c03 |
| C | Small-cluster inference to correlated many-body prediction | Built c02 |
| D | Abelian protection to SU(3) loop-string-hadron constraints | Author data found; runnable author code not recovered |
| E | Ideal occupations to imperfect real correlated readout | Built c01 |
| F | Coherent/white-noise workflow to calibrated colored open dynamics | Built c04 |
| G | Gauge-protection versus spurious-localization ablation | Source-grounded candidate; reference implementation not recovered |
| H | High-penalty accuracy, digital aliases, and runtime tradeoffs | Incorporated into c02/c03; not a fifth pilot |

The original target's own public repository/fix history was not recovered. The
archived experimental code and data, later papers, downstream toolkit fixes,
repository history limitations and request-only code are distinguished in
`authoring/history_research.md` and the candidate register. No missing commit or
author implementation is invented. The supplementary GitHub API audit encountered
HTTP 403; the independently retrieved QuTiP patch supplies concrete A evidence.

## Four minimal pilots

| Pilot | Independent work | Scale / families | Privileged reference |
| --- | --- | --- | --- |
| c01_correlated_tomography | Weighted readout fit; sharp correlated-population bounds and witnesses | 20 real traces; four observation/support families | Archived experimental data plus independently checked conditional inverse model |
| c02_multiscale_protection | Fault calibration; correlated propagation; gauge and correlation observables | 32--48 cells initially, local dimension 4--6; full, linear spin-one, weak/inhomogeneous | Precomputed tensor-network outputs using pinned existing engines; exact small-system checks |
| c03_resonance_compiler | Operator/sector compilation; bounded analog and digital synthesis | 32--160 sites; U1 local, U1 correlated, Z2 pseudogenerators | Feasible constructive/precomputed controls and independently verified transfer certificates |
| c04_colored_noise | Spectrum inference; degenerate frequency-block generator; dynamics and decision | Hilbert dimension 64; white/coherent, pink/correlated, brown/degenerate | Secular-model reimplementation with 22 independent invariant/limit checks |

These are not advertised as four recovered official implementations. In particular,
c03 is a new synthesis wrapper around source constructions, and c04 uses declared
regularization/correlation/crosstalk extensions. C01's outputs are conditional
identified-set bounds, not otherwise unavailable true populations. C02 uses
existing tensor software rather than an invented many-body algorithm. Each
pilot has its own provenance and preconstruction anti-compression assessment.

## Measured initial tournament results

All numbers below are actual isolated evaluations. Full per-case values, errors,
runtime, memory, commands, and hashes are retained under `authoring/runs/`.

| Pilot | Reference mean / worst | Fresh screening mean / worst | Fresh private challenge mean / worst | Attempt duration |
| --- | ---: | ---: | ---: | ---: |
| c01 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 623.48 s, normal exit |
| c02 | 1.000 / 1.000 | 0.999607 / 0.999293 | 0.999776 / 0.999692 | 2938.71 s, normal exit |
| c03 | 0.96638 / 0.96638 | 0.97957 / 0.97164 | 0.98303 / 0.97696 | 1540.03 s, normal exit |
| c04 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 834.77 s, normal exit |

Reference values for c03 hold on all three frozen splits, using feasible anchors,
not proven global optima. Weak baseline means are c01=0.500, c03=0.13572 and
c04=0.574067 on screening. C02's large-state direct-memory lower bounds are in
`authoring/dense_scale_audit.json`; every full state exceeds the public memory
limit. Its independent exact small-system errors are below 2e-7.
C02's measured weak screening baseline is 0.101809 mean / 0.100000 worst-family.
All 21 initial references now pass independent coarse/fine checks, with
normalized conservative comparison scores of at least 0.9822. Their density,
positivity, covariance, and conserved-charge checks also pass; the largest
alternating-charge residual is 6.14e-9. The oracle's 1.000
self-score is only an isolated interface check, not the scientific validation.

### Universal shortcuts already demonstrated

- C01: a fixed weighted linear fit plus linear programming solves all 12 screening
  and four private challenge cases, including missing observations and leakage
  supports. No substantive failure is present. This pilot is solved, not hard.
- C04: a general inference/frequency-resolved propagation implementation solves
  all nine screening and six private challenge cases. Calibration, audit,
  dynamics and decision components each score 1.000. A later long-time probe
  exposes a genuine runtime gap, but that gap does not survive fresh confirmation.
- C03: all completed screening certificates are exact, and compiled numerical
  search reaches or improves the feasible analog/digital reference anchors.
  Corrected screening is solved. Two initial zeros were namespace-startup
  timeouts, not scientific failures; both unchanged submissions finish in about
  52.1 worker seconds under the published 60-second solver limit.
  All 12 private challenge cases also pass robustly; the worst family exceeds
  0.976. A small gap below one is not a substantive unsolved component.
- C02: calibration plus an adaptive, parity-blocked MPS implementation solves
  all six screening and nine private challenge cases. Every case exceeds
  0.99894, including spin-one and weak/inhomogeneous branches. Runtime is
  102.33--3126.75 worker seconds; peak RSS is 812,816 KiB. The realistic dense
  memory barrier does not prevent this specialized fresh solution from succeeding.

## Isolation, fairness, and reference checks

`authoring/run_fresh.py` invokes the supplied `run_allowlisted_codex.sh` with
`--task-read-only`, a fresh empty attempt directory and the requested model.
Only participant/attempt paths and the runner's necessary runtime are allowed.
Each run records the command, runner hash, public input hashes, wall duration,
exit state, and submission hashes under `authoring/runs/`.
For c02, reference precomputation overlaps fresh development. Case seeds and the
public contract are fixed first; only completed, independently converged,
hash-recorded labels are used in evaluation. Reference generation is not tuned
against submitted errors. The final integrity audit verifies 237 frozen files,
all five public trees, and all recorded submission source files.

Untrusted evaluation is a separate network-isolated `bwrap` process. A canary
verified public readability and denial of private references, sibling concepts,
author sources, home configuration, and network access. A nested-sandbox namespace
failure was treated as author infrastructure, not participant failure. The first
launch printed an stdin warning but proceeded normally; a guarded attempted
pre-start stop aborted because model work had begun, and no process was killed
or pilot restarted. Future launches explicitly close inherited stdin.

The compiler timing audit preserves the original screening report and retries
only affected cases. A 30-second namespace-startup allowance does not extend the
strict 60-second worker alarm. Details and correction records are in
`authoring/TIMING_FAIRNESS.md` and the corrected screening JSON. Infrastructure
timeouts do not count toward selecting a hard task.
An isolated timer unit test confirms that a one-second worker deadline interrupts
a five-second sleep even when namespace setup makes total wall time exceed eleven
seconds (`authoring/worker_timer_validation.json`). C02 uses the same separation
before its first scientific evaluation; its solver budget remains 3600 seconds.

Scores are continuous relative to fixed weak and strong anchors. Family and
component results are retained separately. The many-body per-case evaluation
budget was increased from 300 to 3600 seconds **before** fresh launch after
measuring author-reference costs; the agent development budget remains one hour.
This avoids manufacturing hardness by timing out a known valid reference method.
No public task or scoring threshold has been hardened in response to observed
participant results.

## Counterexamples, ratchets, and final selection

The best two remaining counterexample-search leads were c02 and c04. C01 was
already robustly solved. C03's slightly lower smooth score is not an unsolved
optimization gap: all 21 certificates are exact and all 42 analog/digital
objectives meet or exceed the strong reference. It was discarded rather than
ratcheted around artificial score headroom. C02 and c04 received source-grounded
regime probes, without altering their original pools.

C04's short-time pool is solved, but a source-grounded long-time probe establishes
a genuine runtime counterexample. At T=1000 the submission still scores 1.000 in
13.867 worker seconds. At T=10000 it hits the strict 60-second worker alarm, while
the validated accelerated reference scores 1.000 in 0.799 seconds. Two independent
late-time propagators agree within 2.42e-13; trace, positivity, and commutation
checks pass. This is a propagation-cost failure, not evidence of incorrect fitted
physics. Details are in `authoring/c04_longtime_probe/REPORT.md`.

A first c04 ratchet is frozen and its second independent `ultima-alpha` attempt
completed normally in **724.71 seconds**. It uses six new screening and three reserved confirmation cases,
with endpoints 9000--20000; the unlabeled public example uses T=8500. No initial
solution is provided, preserving independent calibration, degenerate-generator,
propagation, and decision work. All 44 frozen hashes pass before launch.

All 18 isolated reference/weak validation calls pass. Reference mean and worst
are 1.000 on both splits, in 0.991--3.581 worker seconds. The fixed weak baseline
is 0.629680 / 0.575000 on screening and 0.643503 / 0.500000 on confirmation.
This version uses a documented stronger white/local secular weak surrogate so
late-time anchors can be measured efficiently; score formulas, weights and
floors are unchanged. These are pre-attempt anchor choices, not score changes
made after seeing the second solution.

The second fresh c04 attempt scores **1.000 mean / 1.000 worst-family** on both
the six screening and three reserved confirmation cases. Every component also
scores 1.000. Thus **c04 is rejected as solved after its genuine runtime
counterexample was overcome**. As precommitted, no second c04 ratchet will merely
increase time, change dimensions, or tighten tolerances.
The submitted generic centered spectral-block method runs in 0.634--2.556 worker
seconds per case, at a peak RSS of 77,472 KiB. Its maximum raw dynamics error is
2.31e-22 and decision regret is zero. All 44 frozen hashes still match; the audit
finds no case-ID lookup or hidden-access code (`authoring/c04_ratchet1_pilot_audit.md`).

C02's original task is also robustly solved. Its two harder spin-one transfer
probes fail reference validation: conservative coarse/fine diagnostics are
0.888478 at T=8 and 0.789787 at T=10, below the precommitted 0.97 gate. Their
observable-charge residuals reach 4.60e-5 and 9.08e-5. A copy-only canonical
measurement audit repairs the coarse charge readout to approximately 1e-14 while
leaving the evolving state unchanged, but accounts for only 0.94--1.69% of the
blockwise coarse/fine gaps. State-truncation convergence remains unresolved.
**No participant was scored against either invalid reference.** The original
21 frozen references are unaffected and pass the same physical checks.

No c02 ratchet is built from an unvalidated private solution. A larger reference
refinement was estimated, not measured, to require roughly 5.5--11.1 hours for
the T=8 case, with no guaranteed convergence; it was not launched. Such a new
author computation is not presented as an already established privileged
capability. The bounded probe evidence is preserved in
`authoring/c02_weakspin_probe/` and `authoring/c02_pilot_audit.md`.

## Final selection

**Accepted task: none. No production participant/private release is emitted.**

Four concepts were built and four initial fresh attempts were completed. One
source-grounded ratchet was built and tested with a fifth independent fresh
attempt. This uses the maximum four concepts and one of the allowed two ratchets
for c04; no extra concept or disguised retest was introduced. C02 and c04 were
the two retained search leads, but only c04 produced a valid counterexample and
therefore a justified ratchet.

The required gates were not relaxed: complete public task; reference above 0.90;
fresh confirmation below 0.70 with worst-family scrutiny; and a substantive
unsolved component. Every completed valid fresh evaluation is above 0.97 in its
worst family. The genuine late-time propagation failure disappears in the fresh
ratchet test. The remaining harder-region labels are unvalidated, not evidence
of participant failure. Neither infrastructure timeouts nor reference defects
are used to manufacture hardness.

This rejects the four tested concepts, not every possible task from the paper.
The unbuilt source directions and unavailable implementation limitations remain
explicit in the candidate register. `tournament_summary.json` indexes the actual
runs; `selection.json` records the final rejection and evidence paths.

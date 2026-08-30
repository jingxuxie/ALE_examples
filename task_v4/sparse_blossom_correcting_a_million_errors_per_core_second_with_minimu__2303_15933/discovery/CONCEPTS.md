# Private discovery ledger

This file is generation-only. It must not be mounted into participant sessions.

## Paper and follow-up inspection

- Seed: Higgott and Gidney, arXiv:2303.15933v2 (14 January 2025), including appendices. Sections 2.1–2.3 specify independent detector mechanisms and distinguish physical MAP from logical maximum likelihood. Section 5 studies distribution-sensitive runtime, while the introduction identifies calibration, correlated decoding and streaming as opportunities beyond the implementation.
- Official implementation: oscarhiggott/PyMatching. Inspected README, benchmarks directory, releases and correlated-matching development. Version 2.4.0 was tagged 22 May 2026, commit prefix 6f63b2b. The task is not a reproduction of this package.
- PR 156 introduced two-pass correlated matching (merged 10 August 2025). PR 169 repaired repeated edge-reweight rollback (merged 20 August 2025). Issue 175 and PR 176 cover a pure-Y construction failure. These later artifacts are privileged context, not participant hints.
- Issue 172 discusses fast edge reweighting. Other open performance issues identify correlation data-structure overhead. Exact package-bug repair was not chosen because later fixes would turn it into source reproduction.
- Follow-up: Takou and Brown, arXiv:2504.20212 (28 April 2025), learns graph/hypergraph error rates using syndrome statistics. This supports active calibration as a scientific extension of the seed, not a claim about any actual processor.
- Independent implementation inspected: yuewuo/fusion-blossom, as context for parallel matching. Parallel-blossom reproduction was rejected.

## Concepts considered before construction

1. **A — Correlated logical decoding improvement (selected).** Improve a supplied two-pass matching baseline over distinct local-noise families on privately sampled logical outcomes, with quality, worst-family and resource constraints. The challenge is posterior ambiguity and robust quality/compute tradeoffs, not implementing the published solver.
2. **B — Robust logical-confidence falsification (selected).** Construct a local detector model and syndrome where the lower-energy physical logical class loses after posterior mass is summed, with nontrivial distance, non-negligible mass and perturbation robustness. The checker uses exact positive probability propagation and independent class-cost certification.
3. **E — Active correlated-fault calibration (selected).** Allocate a limited experiment budget across interventions and recover overlapping rare detector channels from syndromes. Identifiability and simulator checks are required; hidden episodes vary nuisance rates and scientific regimes.
4. **F — Transactional correlated-decoder repair (rejected).** Repair reweight rollback, negative-edge accounting and batch invariance. A real engineering issue, but published later fixes make it too close to reproducing an available patch.
5. **C — Adversarial latency witness (not built).** Find geometrically local syndromes causing a verified growth/queue-work explosion without using mere wall-clock jitter. Potentially interesting, but operation counters require invasive native instrumentation and geometry-dependent thresholds are harder to validate.
6. **D — Rare logical-failure prediction (not built).** Predict low-probability logical failure rates across inhomogeneous detector models using a fixed training corpus. High expected difficulty, but expensive reference uncertainty and distribution specification make this less reliable than the chosen tasks.
7. **A — Streaming/window boundary reconciliation (not built).** Optimize latency/accuracy of a supplied sliding-window decoder under delayed detections. A worthwhile extension, but a clean runnable baseline and scientifically neutral delayed-data model take too much independent machinery.
8. **C — Correlation-preserving graphlike decomposition (not built).** Construct a sparse auxiliary detector embedding preserving selected logical likelihood ratios. Could be difficult, but an unconstrained gadget problem risks structural impossibility or a direct known reduction.
9. **E — Rare-event experimental allocation (not built).** Allocate importance-sampled fault experiments to estimate subthreshold logical rates. Closely connected to the paper's Monte Carlo motivation; independent truth calibration and the distinction between simulation queries and unrestricted local solver calls are more fragile.
10. **B — Local-matching truncation counterexample (rejected).** Defeat a nearest-neighbor truncation using a detector geometry. Usually collapses to a standard adversarial graph gadget and so does not meet the desired substantive hardness.

## Frozen tournament policy

Only the selected three concepts are built. Each receives a completely fresh `ultima-alpha` session, with at most 3600 seconds wall time, participant-only allowlisting, no web, and an initially empty writable submission directory. Targets and evaluator assets are hashed before launch. No evaluator, hidden labels/rates, discovery search, previous submissions, or champion artifacts are provided except a champion explicitly promoted into a later generation's public baseline. Failed valid concepts are retained; solved concepts undergo private search before deciding whether to ratchet, up to three champion generations. No passing privileged solution is presumed.

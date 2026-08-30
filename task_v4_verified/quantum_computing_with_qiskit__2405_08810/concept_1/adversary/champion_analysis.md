# Private champion analysis: concept 1, v_1

Privileged authoring artifact; do not share this note or the prior champion with tested agents. Static inspection only: no submission execution, new scoring, or participant/evaluator modifications. Sources are the completed `scored/v_1/submission`, public task/baseline, and existing generation/stress artifacts.

## Observed status

`scored/v_1/score.json` reports 32 valid cases, **63.57% mean / 58.69% worst-family reduction**, passing the public 40%/25% targets; maximum case time is 11.35 seconds. `stress_score.json` was absent at inspection. The proposed failures below are **hypotheses**, not measured defeats. The existing stress witness summary includes insufficient-headroom cases, so construction alone does not certify challenge feasibility.

## What the champion actually adds

The public baseline is a five-candidate portfolio of routed dynamic/star synthesis (`../participant/baseline/solution.py:134`). The champion is stronger than plain greedy Steiner: native/virtual tree variants, opportunistic rotations, limited lookahead, basis rollback, alternative restoration, cancellation, and scheduling. Its gain therefore does not establish that joint phase-network optimization is solved.

Current planting samples requested parities frequently along a native random walk after warmup (`generate.py:53`). This often leaves nearby requested parities that become cheap in a recently visited basis. Omitting intermediate requests attacks that advantage without changing the public problem.

## Code-level limitations

References below are to `scored/v_1/submission/engine.cpp`.

- **Term-first action space (`:397`, `:453`).** Every forward action gathers one pending parity. Lookahead considers at most four candidate terms and eight roots, rejecting roots above `1.35 * cheapest + 0.5`. Intermediate useful bases can arise accidentally, but there is no explicit action to synthesize a jointly selected target basis before emitting anything.
- **Support count is not future native cost (`:466`).** Lookahead rewards changes in coefficient popcount/log-popcount and newly singleton terms, scaled by a typical edge cost. It does not price future cut crossings, directed calibration, or multi-step amortized benefit. A locally unattractive setup benefiting many later rows can be pruned before actual circuit-cost comparison.
- **Rollback is not multi-step planning (`:429`).** Checkpoints compare the cheapest remaining term with earlier minima, without charging the rollback in that decision. This can undo useful setup. Non-reset portfolio members limit the force of this hypothesis; it is not a guaranteed trap.
- **Linear synthesis is only an ending repair (`:510`, `:658`).** The program can synthesize restoration of its current basis, but never uses that machinery to materialize a desired pending basis. Alternative endings are tried only when inverse-history completion lies within 12% of the incumbent, potentially discarding prefixes with a much cheaper independent restoration.
- **Scheduling is mostly downstream (`:191`, `:612`, `:671`).** Routing uses `error + 0.12 * duration`; final selection uses the correct `error + 0.20 * makespan`. Final rescheduling cannot recover a route/basis excluded earlier. This is secondary to the basis-planning gap, not a claim that a coefficient mismatch alone defeats the champion.

## Assessment of the proposed terminal-basis construction

**Recommended first focus:** choose a short native CX word implementing an invertible matrix M; request its complete row basis, plus a few nearby perturbations; omit all setup-only intermediate masks. Use n=24 or 28 and 24–96 distinct nonzero terms.

Crucial distinction: the matrix is **not concealed information** when its rows are public. What is concealed is a cheap factorization and preferred row placement. With extra terms, a solver can extract candidate bases by ordinary GF(2) elimination. It may choose another placement or interleave rotations; do not require simultaneous realization of M, its planted order, or its planted circuit.

This is a real missing strategy in this champion: globally choose/place a basis, synthesize it, emit a batch, and restore. It is not just another greedy-tree parameter. However, a complete-basis-only family substantially overlaps linear reversible synthesis and could admit a straightforward routed-elimination solution. It is not automatically evidence of a new research-hard problem or an independent replacement for concept 2. Perturbed rows and competing basis covers preserve the phase-network-specific decision.

## Focused valid patterns

1. **Deferred setup with local perturbations.** On a sparse lattice or chorded cycle, plant M, emit its rows, then add 4–12 distinct row-XOR terms from adjacent physical rows. Each perturbation has a native CX/RZ/CX witness that restores M before final uncomputation. Vary setup length, not arbitrary mask density alone.
2. **Amortized cut transport.** Use two connected modules with one or two bridges. Plant a small number of reusable cross-cut combinations, then many within-module updates. Use directional bridge weights up to 12, inexpensive internal edges, and durations 1–6. A good compiler pays setup once; population-count lookahead can repeatedly choose locally cheap but globally expensive alternatives.
3. **Competing overlapping bases.** Mix two related row bases connected by a short native update, plus a few perturbations, keeping at most 96 unique masks. The witness visits the bases coherently and uncomputes. This tests basis selection and traversal beyond extracting one full-rank subset. Deduplicate masks while preserving their independent symbolic term identities.

## Ratchet acceptance

Keep the public objective, baseline, ranges, and family thresholds unchanged. Preserve connected bidirectional topology, no ancillas/permutation shortcuts, and exact identity restoration. Require a checked legal low-cost witness with sufficient aggregate/family headroom; compare champion cost to both baseline and witness. Include matched intermediate-rich controls where feasible and repeat across relabelings/calibrations, not one lucky seed. A single case below 40% is not an aggregate failure. Reject zero-baseline tricks, unsupported operations, timing-only ambushes, or demands to recover private factorization trivia. Main should score candidates in the evaluator sandbox; this note does not establish which pattern wins.

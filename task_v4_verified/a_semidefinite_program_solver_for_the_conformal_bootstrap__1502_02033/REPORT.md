# Empirical hardness report

## Concepts and verification modes

- concept_1: Robust weighted interpolation — A — baseline improvement.
- concept_2: Polynomial-matrix positivity counterexample — B — counterexample/falsification.
- concept_3: Compact exact rational SOS certificates — C — witness construction.

## Scores

| Concept | Baseline core | Fresh attempts (generation: core / worst / resource) | Final status |
|---|---:|---|---|
| concept_1 | 0.9999382 | 1: 1.5336553 / 1.2076233 / 0.90332959 | solved |
| concept_2 | 0 | 1: 1 / 1 / 1; 2: 0 / 0 / 0 | hard_open_candidate |
| concept_3 | 0 | 1: 0.66666667 / 0 / 1 | hard_verified_achievable |

Concept 3's private certificates score 1/1, while the fresh attempt certifies 2/3 blocks.
The remaining approximate identity has a scaled residual of 4.21e-104 but is not exact.
Concept 2's first champion scores 1 on generation 1 and 0 on the strengthened generation 2.
Concept 1's champion is its passing fresh submission: core 1.5336553, worst family 1.2076233, resource 0.90332959. Its fixed targets were 1.15, 1.05, and 0.10, plus a 0.95 minimum-case floor.

## Counterexample search

Interpolation: 160 schema-valid cases across 12 regimes; 13 case pairs received full numerical enclosures and 147 remain triage-only. No confirmed regression emerged. Two timer-limited stress pairs were additionally run through the isolated executable grader and passed quality/resource checks. No failure-based ratchet was justified; this is not a universal optimality claim.
The initial private pilot found 0 successful witnesses in 24 admissible cases. The first fresh agent then found a valid degree-four witness.
A 168-case signed-basis/near-singularity sweep yielded 24 false acceptances under generation 1 and 0 under generation 2.
The clustered failure combines a common nullspace, flat smallest eigenbranch, and an identically zero full determinant. All-principal-minor candidates resolve that cluster.

## Ratchets, solvability, and failed capability

- concept_1: 0 ratchet(s); solvability demonstrated_by_generation_1_fresh_champion. None established: the fresh champion meets the target and the bounded 160-case search finds no confirmed regression.
- concept_2: 1 ratchet(s); solvability unknown_for_strengthened_screen. Constructing a bounded exact-negative matrix polynomial that evades the strengthened all-principal-minor screen; the fresh admissible witness is rejected by all three profiles.
- concept_3: 0 ratchet(s); solvability demonstrated_by_exact_private_witness. Exactification of compact rational SOS factors for the scale-separated degree-18 matrix polynomial: the final approximate identity has 4.21e-104 scaled residual but is not exact; the other two blocks pass.

## Final status

Selected: **concept_3 — hard_verified_achievable**.
Solvability is demonstrated by exact private witnesses; a one-hour isolated ultima-alpha attempt did not produce all required certificates.

# Empirical hardness decision

**Selected task: concept 3 — `hard_verified_achievable`. Solvability is demonstrated.**

## Concepts and verification modes built

| Concept | Primary mode | Ratchets | Task generations | Final status | Solvability |
| --- | --- | ---: | ---: | --- | --- |
| 1. Resource-aware bloq scheduling | A — baseline improvement | 1 | 2 | `solved` | Demonstrated by fresh agents and private schedules |
| 2. Compact silent GQSP failure | B — counterexample/falsification | 2 | 3 | `hard_open_candidate` | Unknown in the final degree-8–12 domain |
| 3. Compact coherent lookup synthesis | C — witness/design construction | 0 | 1 | `hard_verified_achievable` | Six independently verified private designs |

## Baseline and champion scores

- **Scheduling:** each generation's supplied baseline has normalized core score
  1.000000. Generation-1 champion: **2.401462**, worst-family **1.488061**.
  Generation-2 champion: **1.193369**, worst-family **1.193369**, worst-instance
  **1.130743**. Its fixed target is 1.06 aggregate and 1.02 on every instance,
  with the 5% peak guard. The private generation-2 witness scores **1.069385**.
  Ratchet scores use different workload banks and their respective baselines;
  the two champion ratios are not directly comparable across generations.
- **GQSP:** the final baseline is admissible but has minimum RMS error
  **1.19844e-15**, core **2.39688e-14**. The historical degree-48 champion has
  minimum RMS error **1.18967451**; the degree-14 champion has **0.12301800**.
  Both score 1.0 in their original domains and are inadmissible in the final
  degree-8–12 domain. The final target remains **0.05 minimum RMS error across
  all six configurations**, equivalent to core 1.0.
- **Lookup:** baseline **0/6** resource-bounded designs, core/worst-family **0**,
  despite exact truth tables on all six. The private portfolio scores **6/6**,
  core/worst-family/resource **1.0**. Its designs use **20–36 AND gates**;
  the instance caps are **22–38**. No fresh champion exists.

## Fresh-agent scores

All scored attempts use `ultima-alpha` with a 3,600-second cutoff. Timeout
termination has a separately recorded ten-second cleanup grace. One initial
scheduling run with broken PTY support is excluded, not counted as hardness.

| Concept / generation | Attempt | Core | Worst-family | Other decisive metric | Passed |
| --- | --- | ---: | ---: | --- | --- |
| Scheduling / 1 | v_2 | 2.401462 | 1.488061 | All peak guards satisfied | Yes |
| Scheduling / 2 | v_3 | 1.193369 | 1.193369 | Worst instance 1.130743 | Yes |
| GQSP / 1 | v_1 | 1.000000 | 1.000000 | Degree 48; minimum RMS 1.189675 | Yes |
| GQSP / 1 | v_2 | 1.000000 | 1.000000 | Degree 48; minimum RMS 1.159758 | Yes |
| GQSP / 2 | v_3 | 1.000000 | 1.000000 | Degree 14; minimum RMS 0.123018 | Yes |
| GQSP / 2 | v_4 | 1.000000 | 1.000000 | Degree 14; minimum RMS 0.090717 | Yes |
| GQSP / 3 | v_5 | 0.023493 | 0.023493 | Admissible degree 12; minimum RMS 0.001174643 | No |
| GQSP / 3 | v_6 | 0.024839 | 0.024839 | Admissible degree 12; minimum RMS 0.001241975 | No |
| Lookup / 1 | v_1 | 0.000000 | 0.000000 | Exact 6/6; resource-bounded 0/6 | No |
| Lookup / 1 | v_2 | 0.000000 | 0.000000 | Exact 6/6; resource-bounded 0/6 | No |

The final numerical attempts run for 3,596.47 and 3,610.59 seconds including
cleanup; the latter times out. Both lookup attempts reach the cutoff and terminate
after 3,610.30 and 3,610.43 seconds including cleanup. All scored participant
trees remain unchanged, and every run begins with an empty writable output.

## Counterexample and adversarial search results

- **Scheduling:** replaying the first champion on **24 private graphs across
  four families** exposes wide-frontier inefficiency, with a maximum private
  continuation gain of **1.137165**. This seeds the solved second generation.
  A final **24-profile, 120-second-per-profile** continuation sweep produces
  only **1.009736** aggregate additional gain, minimum instance **1.001968**,
  maximum instance **1.021102**. All orders are legal; no further gap meeting
  the fixed meaningful-improvement criterion is found. No optimality is claimed.
- **GQSP:** the original champion's **35,000 compact-domain trials** find no
  passing degree-8–14 witness, but fresh agents subsequently solve degree 14.
  Replaying their directed method in **40,000 trials** over degrees 8, 10, 12
  and 13 finds no smaller passing witness. A further **80,000 privileged
  degree-12 refinement trials** reach minimum RMS **0.0005647283**, still below
  0.05. Neither final fresh agent supplies a valid witness. These negative
  searches establish neither impossibility nor current-domain achievability.
- **Lookup:** private constructions pass all **14,336 truth-table rows** and
  the required clean reversible lift. Independent corruptions reject 24
  resource violations, 36 wrong-row cases and 37 malformed artifacts. Both
  fresh attempts fail before any champion ratchet is needed.

## Substantive capability and final status

- **Scheduling — solved:** no persistent final-target failure. Agents overcome
  the weighted live-register-frontier optimization gap exposed by the first ratchet.
- **GQSP — hard_open_candidate:** agents fail to construct a robust compact
  numerical counterexample while preserving density, global contraction,
  accurate completion and nonzero phase guards. Solvability remains **unknown**;
  larger-degree historical witnesses are not evidence of final-domain feasibility.
- **Lookup — hard_verified_achievable, selected:** agents reproduce every output
  exactly and meet the depth bounds, but fail to recover compact shared nonlinear
  structure. Attempt v_1 uses **110–326 AND gates** and v_2 **128–378**, against
  caps of **22–38**; affine-size and clean-workspace caps also fail on every
  instance. Private designs prove the simultaneous requirements achievable.

These are empirical decisions for the stated model and budgets, not claims of
universal computational hardness. Machine-readable scores and decisions are in
`report.json` and the individual `status.json` files.

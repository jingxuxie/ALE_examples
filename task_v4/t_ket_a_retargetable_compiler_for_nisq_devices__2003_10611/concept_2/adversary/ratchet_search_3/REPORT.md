# Final G3 private audit

G3 remains solved. No task, score, policy, or frozen artifact changed.

## Fixed-method robustness

All 32/32 additional deterministic families meet the original targets.
The 11 logical, 11 physical, and 10 joint permutations were declared before evaluation.
All 1,984 returned policy routes and 32 transformed reference routes were exactly replayed;
the original reference also undergoes 33 validator replays in this phase.
Portfolio SWAP range: 55–76.
Worst ratios: SWAP 3.66666667, native 1.71428571; gap 40.

## General repairs

Both variants examine tail trims 1..8 and core starts at multiples of four.
They use the frozen embedding and token budgets; every prefix, layout transition, and tail is paid.
The second variant chooses each prefix from all 62 frozen G3 policies, without recursion into this repair.
- repair_summary.json: 51–51 SWAPs; families below target: none; 12 completed calls including 6 independent controls.
- repair_summary_portfolio.json: 37–39 SWAPs; families below target: identity, logical-47, physical-11; 12 completed calls including 6 independent controls.

With frozen-portfolio prefixes, the exact repaired cost is 37 SWAPs in identity, physical-11,
and logical-47; it is 39 in the other three public families. At 37, the SWAP ratio is 37/15 < 2.5.
Thus this separate repair breaks the all-families-required condition in three families, not uniformly.
Its best decomposition is prefix 30/32 + layout 6 + terminal tail 1, at core start 80 and trim 1.
This is an audit of a new general policy, not a change to the frozen evaluator or its solved status.

## Root evidence

The final three demands form a logical triangle, executed with one reference SWAP.
The ladder hardware is bipartite. Every one of the 31 all-program cutoffs retains that triangle,
so neither frozen static-suffix embedding policy can embed its entire suffix at any cutoff.
The reference additionally changes layout in multiple earlier phases; allowing a terminal tail alone
does not ensure a cheap prefix. The fixed-prefix repair costs 51 SWAPs and does not break the target.
Full routes, search counters, exact family measurements, and the reference swap schedule are private artifacts here.

No fresh agents launched; no further generation.

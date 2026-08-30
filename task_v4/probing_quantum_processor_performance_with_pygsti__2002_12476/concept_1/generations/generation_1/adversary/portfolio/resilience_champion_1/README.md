# Private champion-relative two-circuit-loss feasibility

This directory contains generation-time evidence, not a fresh-agent attempt or
a hardness decision. The only fresh-agent artifact read is the explicitly
authorized `concept_1/champions/generation_1/design.json`. No attempt directory
was inspected. All new writes are confined to this directory; all older
portfolio designs, audits, and search code remain unchanged.

## Fixed objective and reference

The comparator is the official generation-1 static champion, SHA-256
`4d48578f30ab4dae53a3b57fa1eeb2c4fcc6476df47c29496221bd542e8bb58d`.
`reference_design.json`, `reference_scores.json`, and `contract.json` freeze
that comparator, the original 60 hidden operating points, and the requested
targets before this search.

For each operating point separately, remove all batches of every possible
pair of selected circuits, invert the remaining 14-parameter information
matrix, and maximize the first-12-coordinate A-risk over those pairs. Average
those per-point maxima overall and within each regime. There is no loss-time
reallocation. With 24 selected circuits, all 276 pairs are considered.

The required reductions are at least 50% overall and 30% in each of the six
regimes; intact mean A-risk must not exceed 1.20 times the champion's. The
original 1,600,000-tick budget, 12,000-tick per-circuit setup cost, 64-shot
batches, maximum 48 batches per circuit, and 24-of-840 support cap apply.
Single-loss scores in the audit files are diagnostic, not additional targets.

## Preserved passing proof

`design.json` and `first_passing_design.json` are identical preserved passing
artifacts. `score.json` and `first_passing_score.json` contain exact scores.
The design SHA-256 is
`01c1086bae6173bf4061a6271b7f842bf8a7791fc18bdb533888da9fb40888cb`.

| Quantity | Champion | Passing design |
| --- | ---: | ---: |
| Mean worst-two-loss A-risk | 528.0855597715653 | 22.074259638652293 |
| Intact mean A-risk | 4.71501662977593 | 5.502099044112409 |
| Overall two-loss reduction | — | 0.9581994636471389 |
| Worst-family reduction | — | 0.4337869339813447 |
| Intact ratio | 1 | 1.1669309943396495 |
| Execution ticks | — | 1,599,104 |
| Distinct circuits / batches | — | 24 / 514 |

All six exact family reductions are: anisotropic 0.9240670753, detuned
0.6032890330, long coherence 0.8309302554, mixed 0.4337869340, near nominal
0.9205212353, and readout 0.9903094036. This demonstrates achievability of the
fixed requested target; a fresh challenger still must determine hardness.

The initial portfolio used the prior private single- and double-loss designs
and the authorized champion. It optimized continuous resource fractions under
hard intact/family guards, exchanged sparsity support over all 840 candidates,
then restored integral shot batches under the physical budget. The objective
balances normalized family risks rather than allowing the champion's large
readout losses to dominate. The first pass appeared after 71.825 seconds, in
the first support-exchange round, and search stopped after 72.024 seconds.

## Population validation and its limits

`audit_summary.json` evaluates the preserved proof without changing it.

| Draw set | Points | Overall reduction | Worst family | Intact ratio | All targets |
| --- | ---: | ---: | ---: | ---: | --- |
| Frozen hidden | 60 | 0.958199464 | 0.433786934 | 1.166930994 | Pass |
| Broader private draws | 3,000 | 0.862513333 | 0.159153903 | 1.237363394 | Fail |
| New draws, seed 71389201 | 600 | 0.861093324 | 0.379334040 | 1.238601710 | Fail |

The broader set has 500 draws per family and was used in older private
portfolio work, but not in the initial champion-relative search. The 600 new
draws have 100 per family and were not used in optimization. The broad miss is
in mixed-family reduction and the intact guard; the 600-draw miss is only the
intact guard. Thus the preserved proof establishes the frozen finite benchmark,
not population-wide satisfaction of every threshold.

`refine_population.py` performs a separate bounded refinement using 300 broad
training points, a 42-candidate private support pool, and full 3,000-point
selection checks. It writes only `robust_design.json`, `robust_score.json`,
and population-search artifacts, never overwriting the preserved proof.
The original broad/fresh audit files also remain available for comparison.

The refinement stopped after 378.863 seconds (finishing the active exchange
after its 360-second deadline). It produced another exact frozen-target pass,
saved separately as `robust_design.json` with flat canonical scores in
`robust_exact_score.json`: mean loss risk 27.6700669496, intact mean risk
5.3177886946, 24 circuits, 552 batches, and 1,599,808 execution ticks.

| Refined-design draw set | Overall reduction | Worst family | Intact ratio | All targets |
| --- | ---: | ---: | ---: | --- |
| Frozen hidden, 60 | 0.947603061 | 0.483826801 | 1.127840920 | Pass |
| Broad selection set, 3,000 | 0.777309136 | 0.242342794 | 1.164562049 | Fail |
| Earlier new draws, 600 | 0.819943867 | 0.459915836 | 1.166677127 | Pass |
| Independent confirmation, 600 | 0.766105779 | 0.274661337 | 1.178349839 | Fail |

The confirmation seed is 99583321. These additional 600 operating points were
not inspected or used to fit/select the refined design; their scores were
computed only after refinement stopped. The earlier 600-point audit was seen
before refinement, although its points were not used in optimization or
selection. The broad and confirmation failures are both solely the mixed-family
30% reduction guard. Thus two separate designs prove the requested frozen
target achievable, while satisfaction of all thresholds on the broader
challenge sets remains undemonstrated by this bounded search.

`robust_audit_summary.json` contains the four complete refined-design audits;
`robust_*_root_clusters.json` retains their failure mechanisms. Independent
linear-solve reconstruction also checks the refined design, with maximum
relative two-loss disagreement 2.63e-14. `summary.json` records both preserved
and refined evidence separately.

## Root causes and numerical checks

`root_cause_clusters.json` groups failures by the largest target-coordinate
variance increase after each operating point's worst pair loss. The detailed
`hidden_root_clusters.json`, `broad_root_clusters.json`, and
`fresh_root_clusters.json` also contain exact circuit definitions, operating
points, family counts, leading variance increments, and worst-loss eigenvalues.

The champion's mean loss-induced increase is 523.3705431, of which 506.4586545
is the idle-Y coherent-error coordinate. The idle-Y-dominated cluster contains
39 of 60 operating points. Pairs `(294,752)` and `(124,752)` are worst at 22 and
6 points respectively. These are idle-sequence probes; removing their joint
sensitivity leaves a nearly unidentifiable idle-Y direction. The worst
champion point is a readout-family point with A-risk 17,948.9024252.

The preserved proof's mean loss-induced increase falls to 16.5721606. Its
remaining major clusters are X-depolarization separation (24 points), Y-x
coherent error (7), Y-y coherent error (9), and idle-depolarization separation
(8). Its worst hidden point has A-risk 85.9054048. These are meaningful
parameter-identifiability failures, not arbitrary circuit-ID conditions.

`verify_numerics.py` independently rebuilds each remaining information matrix
from surviving rank-one contributions and uses linear solves rather than the
optimizer's Woodbury formulas. Maximum relative disagreement is 1.12e-13 for
the passing design and 2.70e-14 for the champion. Analytic objective, intact,
and family gradients agree with centered finite differences to 3.40e-8 or
better. Direct inverses versus Woodbury agree within 2.84e-9 across all 3,660
audited points, including the large champion tail. The 1e-10 ridge is unchanged.
The protected-file check covers 64 old/public/champion paths; none changed.

## Run

Run from `concept_1/`, with the installed `/usr/bin/python`, NumPy, and SciPy:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
BASE=adversary/portfolio/resilience_champion_1
/usr/bin/python "$BASE/optimize.py" --seconds 950
/usr/bin/python "$BASE/rebased.py" --submission "$BASE/design.json"
/usr/bin/python "$BASE/audit_candidate.py"
/usr/bin/python "$BASE/verify_numerics.py"
/usr/bin/python "$BASE/finalize.py"
/usr/bin/python "$BASE/refine_population.py" --seconds 360 --per-family 50
/usr/bin/python "$BASE/audit_candidate.py" --submission robust_design.json --prefix robust_ --datasets hidden broad fresh confirmation
```

The scripts read frozen public/native assets and reuse pure numerical routines
from the older private `resilience/` directory. `optimize.py` and
`refine_population.py` have separate logs. `summary.json` indexes the preserved
proof, exact scores, population diagnostics, protected hashes, and numerical
checks. Generation-time optimizer and hidden assets must remain unavailable
to any fresh challenger.

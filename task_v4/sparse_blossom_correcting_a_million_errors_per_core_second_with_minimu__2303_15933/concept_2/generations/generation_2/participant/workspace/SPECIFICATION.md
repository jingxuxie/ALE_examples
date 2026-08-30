# Generation-two contract

## Fixed graph, probabilities, and submission

The unchanged graph has five columns and four detector rows. Detector
`(column,row)` is `4*column+row`. There are left boundary half-edges at column 0,
right boundary half-edges at column 4, and all horizontal/vertical nearest-neighbor
edges. No other edges may be added. Only left half-edges flip the logical bit.

Edges 0–23 are ordered by cut `0..5`, then row `0..3`, with index `4*cut+row`.
Cut 0 is the left half-edge, cut 5 the right half-edge, and other cuts join columns
`cut-1` and `cut`. Edges `24+3*column+row`, for column `0..4` and row `0..2`, join
adjacent rows. `input/graph.json` explicitly lists the incidences. Boundary
vertices are unmeasured; a half-edge flips its one incident detector.

Maximum detector degree is four. There are no parallel, diagonal, self-loop, or
zero-detector edges. Zero-syndrome odd-logical subsets must cross the boundaries
and contain at least six edges; a straight path attains six. This is a synthetic
local graphlike independent-error model, not a circuit-noise calibration claim.

Submit a regular UTF-8 JSON file of at most 16,384 bytes, with exactly:

- `version`: integer `1`, not `true` or `1.0`. Task generation does not change this field.
- `probabilities`: 39 finite numbers, each in [0.02,0.14], in the stated edge order.
- `syndrome`: 3–6 distinct sorted integer detector indices in [0,19].

The base probabilities have arithmetic mean ≤0.085 and population standard
deviation ≥0.015. The syndrome occupies at least three distinct rows and three
distinct columns. Booleans in numeric fields, strings, duplicate object keys,
NaN/infinity, extra fields, nonregular files, and symlinks are rejected. Binary64
conversion precedes numerical comparisons. `witness.schema.json` is supplementary:
the checker also enforces sorting, spatial spread, arithmetic constraints, and
the strict integer representation for version/detectors.

Base-design bounds are checked once. Calibrated probabilities are NOT clipped or
rejected for crossing a nominal bound. Their possible range [0.01805,0.15435]
remains physical and strictly below one half.

## Exact physical and logical quantities

For any calibrated vector `q`, an edge subset has independent probability
`product(q[edge] if present else 1-q[edge])`. XOR detector incidences for its
syndrome and left-boundary incidences for its logical bit. Let `joint[logical]`
sum these probabilities over every subset with the submitted syndrome and that
logical bit. Let `cost[logical]` minimize `sum(log((1-q)/q))` over the same subsets.
Logs are natural and `joint` is unconditional, not normalized within a class.

At unperturbed base probabilities choose `physical` as the lower-cost class, with
class 0 for an exact tie. Keep this SAME class throughout every calibration;
write `opposite=1-physical`. The signed gap is `cost[opposite]-cost[physical]`,
the opposite posterior is `joint[opposite]/sum(joint)`, and syndrome probability
is `sum(joint)`. The opposite log odds are `log(joint[opposite]/joint[physical])`.
Weighted degeneracy can reverse these odds despite the physical cost advantage.

## Domain A: original global calibration

For every real `alpha` in [0.95,1.05], use `q[edge]=alpha*p[edge]`. The original
certificate is unchanged: 21 anchors `0.95,0.955,...,1.05`, derivative bound

```
D_global = 39/0.95 + sum(p[edge]/(1-1.05*p[edge]))
```

The certified targets are gap ≥1.08, opposite posterior ≥0.85, and syndrome
probability ≥0.0000175. This entire original requirement is retained.

## Domain B: explicit spatial calibration lines

There are seven row directions and fifteen column directions. To enumerate a
row direction, choose a four-entry sign vector from {-1,+1}, with first entry +1,
excluding the all-+1 vector. For a column direction use the analogous five-entry
vector. All such vectors are included: there are no hidden, sampled, or selected
directions. Alternating/staggered patterns are automatically included. The first
sign convention removes duplicate sign reversals because amplitudes can be negative.

Assign each detector its row's or column's sign. For an internal edge, `raw[edge]`
is the average of its two detector signs; for a boundary half-edge it is its one
detector's sign. Normalize using the submitted base probabilities:

```
center = sum(p[edge]*raw[edge]) / sum(p[edge])
centered[edge] = raw[edge] - center
direction[edge] = centered[edge] / max(abs(centered))
```

The denominator is nonzero for every declared direction. Thus
`max(abs(direction))=1` and `sum(p*direction)=0`. For EACH direction and EACH
background scale `background` in the two-element set {0.95,1.05}, require the
entire continuous line

```
q[edge](amplitude) = background*p[edge]*(1+amplitude*direction[edge])
amplitude in [-0.05,0.05]
```

Every local multiplier lies within ±5%, and `sum(q)=background*sum(p)` for all
amplitudes. There are 44 spatial lines, plus the original global line: **45
one-dimensional domains**. This does NOT cover arbitrary independent row/column
amplitudes, mixtures of directions, or every pair of intermediate global scale
and nonzero local amplitude. No corner-extremum theorem is assumed.

Spatial-line certificate targets are gap ≥0.85, opposite posterior ≥0.845,
and syndrome probability ≥0.0000175. The modestly relaxed local margins are
additional requirements, not substitutes for the original global targets.

Use 51 anchors `-0.05,-0.048,...,0.05` on each spatial line. Write `height=0.05`
and let `absolute=abs(direction[edge])`. Its derivative bound is

```
D_local = sum(absolute / ((1-height*absolute)
                         *(1-background*p[edge]*(1+height*absolute))))
```

## Continuous certificates and proof

For either kind of line, let `radius` be half its largest adjacent anchor spacing,
and `allowance = D*radius + 1e-10`. Compute

```
certified_gap = min(anchor signed gaps) - allowance
certified_log_odds = min(anchor opposite log odds) - allowance
certified_opposite_posterior = 1/(1+exp(-certified_log_odds))
certified_syndrome_probability = min(anchor syndrome probabilities)*exp(-allowance)
```

All three certificate bounds must meet that line's targets. A true physical
inversion that misses the specified sufficient certificate is not a pass.

For a local edge with direction `direction`, the two possible log-probability
derivatives are `direction/(1+amplitude*direction)` for a present edge and
`-background*p*direction/(1-q)` for an absent edge. Their difference has magnitude
`abs(direction)/((1+amplitude*direction)*(1-q))`, bounded by its term in D_local.
Thus the range of configuration log-probability derivatives has width ≤D_local.
Log derivatives of nonnegative class sums are weighted averages inside this
same range, so the opposite log-odds derivative has absolute value ≤D_local.
Each edge's two derivatives have opposite signs, also bounding the absolute
log-syndrome-probability derivative by D_local.

Edge-cost derivatives are `-direction/((1+amplitude*direction)*(1-q))`.
All subset-cost slopes lie between the sum of the negative edge derivatives
and the sum of the positive ones, an interval of width ≤D_local. Each class
minimum has a slope in that interval wherever differentiable. Their difference
is therefore D_local-Lipschitz, including at minimum-cost kinks: there is no
missing factor of two. The analogous global derivative argument yields D_global.
Every point of each declared line is within radius of an anchor. Positive
certified gaps guarantee that the fixed physical class never switches.

The `1e-10` guard is conservative against binary64 roundoff. Exact inference
means exhaustive combinatorial summation/minimization, not symbolic rational
arithmetic. No Monte Carlo, truncation, shortest-path counting approximation,
or matching-package behavior enters acceptance.

## Scores, APIs, and resources

A line's score is the nonnegative part of the minimum of its certified gap/target,
certified log odds/target log odds, and certified syndrome probability/target.
`core_score` is the minimum score over all 45 lines. `nominal_score` is the global
line's score; `local_score` and `worst_family_score` are the minimum spatial-line
score. `worst_scale_score` is the minimum normalized anchor score before interval
allowances, diagnostic only. All certificates must pass. Runtime/resource scores
are 1 for valid artifacts and 0 for invalid ones; inference speed is not rewarded.

`workspace/check.py` exposes `load_submission`, `validate`, `frontier`,
`calibrations`, and `check`. `calibrations(data)` lists every line, its probability
matrix, derivative bound, and targets. `frontier` returns both unconditional
class masses and both minimum costs. `--summary-only` suppresses detailed groups
on stdout, while `--output` still saves the full result.

There are 2,265 exact inference points: 21 global plus 44*51 local. The trusted
checker independently constructs the calibration schedule and processes all
syndrome-plus-logical states, with a reversible binary basis change for efficiency.
It does not import the public checker or use any reference witness. The public
checker instead eliminates detector columns with a small frontier.

Construction has a fixed 3,600-second wall budget. Trusted evaluation separately
has a nominal 900-second allowance, one CPU thread, and 1 GiB. Shared-host
scheduling delay is not a scientific failure; no internal wall watchdog changes
acceptance. Only JSON is submitted; no submitted code is executed.

## Provenance and scientific scope

Both previous fresh attempts passed generation one independently. The supplied
baseline is the actual promoted best artifact, with selection and original
metrics in `baseline/`. Spatial calibration stress produced genuine pointwise
gap and posterior failures, not just missed lower-bound certificates. Generation
two therefore adds a new uncertainty domain rather than merely tightening numbers.

Higgott and Gidney, *Sparse Blossom*, arXiv:2303.15933v2, sections 2.1–2.3, provides
the physical-MAP/logical-ML distinction. Relevant primary context includes Bravyi,
Suchara and Vargo, arXiv:1405.4883; Smith, Brown and Bartlett, DOI
`10.1038/s42005-024-01883-4`; and Lin, arXiv:2510.06531. The proposed universal
confidence inference is stronger than any theorem asserted here from those
papers. This task does not challenge exact matching correctness or their
empirical/asymptotic results.

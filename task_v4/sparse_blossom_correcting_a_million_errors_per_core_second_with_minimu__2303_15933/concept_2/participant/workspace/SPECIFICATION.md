# Exact contract

## Fixed graph and edge ordering

There are five detector columns and four rows. Detector `(column, row)` has index
`4*column + row`, with column in `0..4`, row in `0..3`. Horizontal nearest-neighbor
edges join adjacent columns. Vertical nearest-neighbor edges join adjacent rows.
Every detector in column 0 has a left boundary half-edge, and every detector in
column 4 has a right boundary half-edge. No other boundary edges exist. Boundaries
are unmeasured: a half-edge flips only its incident detector.

The 24 horizontal/boundary edges come first. For `cut=0..5`, `row=0..3`, edge
`4*cut+row` is the left half-edge if cut is 0, the right half-edge if cut is 5,
or joins columns `cut-1` and `cut` in that row otherwise. The remaining 15 edges
are vertical: edge `24+3*column+row` joins `(column,row)` to `(column,row+1)`.
Only the four left half-edges flip the logical bit. `input/graph.json` lists every
edge, endpoint, and logical label explicitly.

Detector degree is at most four, and there are no parallel, diagonal, self-loop,
or zero-detector edges. A zero-syndrome logical error must connect the two different
boundaries and has at least six edges; a straight horizontal path attains six.
The distance is thus six. Contractible cycles and same-boundary paths have even
left-boundary parity. This is a synthetic local graphlike error model, not a full
circuit-level noise model or a hardware calibration claim.

## Submission

The entire artifact is a UTF-8 JSON object with exactly these fields:

- `version`: integer `1`, not `true` or `1.0`.
- `probabilities`: exactly 39 finite JSON numbers, in the edge order above.
- `syndrome`: a sorted list of 3–6 distinct integer detector indices in `0..19`.

Each base probability is in the inclusive interval `[0.02,0.14]`; the arithmetic
mean is at most `0.085`; the population standard deviation is at least `0.015`.
Syndrome indices must occupy at least three distinct rows and three distinct
columns. Numerical comparisons are made after binary64 JSON conversion. The
artifact is at most 16,384 bytes. Booleans, strings in numeric fields, NaN, infinity,
duplicate object keys, extra fields, symlinks, and nonregular files are rejected.
The optional machine-readable JSON schema complements, but does not replace, the
arithmetic and spatial constraints in this document.

## Physical MAP and logical ML

At scale `alpha`, edge `edge` occurs independently with probability
`q_edge = alpha * probabilities[edge]`. This scales probabilities, not odds or
weights. All evaluated probabilities remain strictly below one half. For an edge
subset `error`, XOR its detector incidences to get its syndrome, and XOR its left
boundary incidences to get logical bit `logical`.

Let `joint[logical]` be the **unconditional** sum of
`product(q_edge if present else 1-q_edge)` over every error subset with the
submitted syndrome and that logical bit. The syndrome probability is
`mass = joint[0]+joint[1]`. Let `cost[logical]` be the minimum, over the same subsets,
of `sum(log((1-q_edge)/q_edge))` on present edges; logarithms are natural.

At alpha=1 choose `physical` as the class of smaller cost (class 0 for an exact
tie). Always compare this *same* class across the whole interval. Write
`opposite=1-physical`, `gap=cost[opposite]-cost[physical]`, and
`log_odds=log(joint[opposite]/joint[physical])`. The contrary logical posterior is
`joint[opposite]/mass`. Neither individual minimum-error probabilities nor counts
of shortest paths are the logical posterior.

For intuition, if `multiplicity[logical]` is the sum of
`exp(-(error_cost-cost[logical]))` in that class, then
`log_odds = -gap + log(multiplicity[opposite]/multiplicity[physical])`.
The desired effect is weighted degeneracy, not a matching-package bug. The two
classes actually contain the same number of configurations; their weighted sums
need not agree.

## Continuous robustness certificate

The required result is over **every real alpha in [0.95,1.05]**, not just three
or twenty-one isolated calibrations. The official acceptance rule is a fixed,
conservative sufficient certificate, evaluated exactly as follows.

Use the 21 anchors `0.95,0.955,...,1.05`. Set

```
D = 39/0.95 + sum(probability/(1-1.05*probability))
r = max(adjacent anchor spacing)/2
allowance = D*r + 1e-10
certified_gap = min(anchor gaps) - allowance
certified_log_odds = min(anchor log_odds) - allowance
certified_opposite_posterior = 1/(1+exp(-certified_log_odds))
certified_syndrome_probability = min(anchor masses)*exp(-allowance)
```

Acceptance requires `certified_gap >= 1.08`,
`certified_opposite_posterior >= 0.85`, and
`certified_syndrome_probability >= 0.0000175`. A physically valid inversion that
misses this certificate is not a pass. There is no hidden rounding slack.

Here is why the interval deduction is sound. For any physical subset, its
log-probability derivative lies between `-sum(p/(1-alpha*p))` and `39/alpha`.
The same bounds apply to a nonnegative sum of subset probabilities by weighted
averaging. The absolute derivative of a log ratio of two such sums is at most D;
the absolute derivative of log syndrome mass is also at most D. Each edge weight
has derivative `-1/(alpha*(1-alpha*p))`. Every subset cost and each class minimum
therefore has slopes between `-D` and zero, making the difference of two class
minima D-Lipschitz, including at their kinks. Every point is within r of an anchor.
The positive certified gap also guarantees the selected physical class cannot
change. The `1e-10` guard is conservative against binary64 roundoff.

The progress score is `max(0,min(certified_gap/1.08,
certified_log_odds/log(0.85/0.15), certified_syndrome_probability/0.0000175))`.
Higher is better; score at least one corresponds to meeting all targets, subject
to validation. Invalid artifacts score zero. Runtime does not enter the score.
`worst_family_score` repeats the certified continuous score; `worst_scale_score`
is the minimum normalized score at the 21 anchors before interval allowances,
and is diagnostic only. `runtime_score` and `resource_score` are 1 for valid
artifacts and 0 for invalid artifacts, not speed rewards. Official results include
a standardized reason, wall/CPU seconds, peak resident memory, and resource policy.

## Checker and inference

`workspace/check.py` exposes `load_submission(path)`, `validate(data)`,
`frontier(probabilities, syndrome, scale)`, and `check(data)`. The frontier function
returns two arrays: unconditional class masses and minimum class costs. It sums
all subsets, retaining four horizontal parity bits and the logical bit while
eliminating columns. Its lower-level function is for trusted numeric inputs;
use `check` or the CLI to enforce the full artifact contract.

The independent official oracle instead has `2**21` syndrome-plus-logical states.
Initially only state zero has mass 1 and cost 0. For each edge mask `mask` it uses
fresh arrays with `new_mass[state]=(1-q)*mass[state]+q*mass[state XOR mask]` and
`new_cost[state]=min(cost[state],weight+cost[state XOR mask])`. No truncation,
Monte Carlo, alternating-sign Fourier transform, or decoder library is used.
“Exact” means exhaustive combinatorial inference with binary64 arithmetic and
the stated numerical guard, not symbolic rational output.

The coding budget is 3,600 wall seconds. Evaluation is trusted artifact-only
computation, allowed 1 GiB and a generous 3,600-second independent wall allowance
on the loaded shared host; it is not deducted from the coding budget. It normally
takes much less. Python 3 with NumPy suffices; no network access is needed.
There is no internal wall watchdog or score penalty for shared-host contention.

## Research context

- Higgott and Gidney, *Sparse Blossom*, arXiv:2303.15933v2 (January 14, 2025),
  sections 2.1–2.3: detector/logical incidence, independent graphlike errors, and
  the physical-MAP versus logical-ML distinction.
- Bravyi, Suchara, and Vargo, *Efficient Algorithms for Maximum Likelihood
  Decoding in the Surface Code*, arXiv:1405.4883 (2014): exact and approximate
  logical-likelihood inference, an antecedent rather than a followup.
- Smith, Brown, and Bartlett, *Mitigating errors in logical qubits*,
  Communications Physics 7, 386 (November 28, 2024), DOI
  `10.1038/s42005-024-01883-4`: confidence selection using inequivalent correction
  costs. The present constrained counterexample does not refute that paper's
  empirical or asymptotic results.
- Lin, *Approximate maximum likelihood decoding with K minimum weight
  matchings*, arXiv:2510.06531 (October 8, 2025): aggregating multiple likely
  physical configurations to approximate logical likelihood.

The proposed universal confidence inference in TASK.md is deliberately stronger
than a theorem from any cited paper. Its falsification is the task.

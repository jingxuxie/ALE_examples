# Complete generation-three specification

## Artifact and graph

Submit exactly `{"version":1,"probabilities":[39 numbers],"syndrome":[detector ids]}`.
The file must be a regular nonsymlink UTF-8 JSON file of at most 16,384 bytes.
Duplicate keys, extra keys, booleans in numeric fields, nonfinite values, and
noninteger version/detector ids are invalid. Version must be the integer 1.
Every nominal probability is in [0.02,0.14], their arithmetic mean is at most
0.085, and their population standard deviation is at least 0.015. The syndrome
is a sorted list of 3–6 distinct ids, occupying at least three rows and three
columns. `input/witness.schema.json` documents the structural portion; the
checker also enforces the numerical and spatial conditions.

Detector `(column,row)` has id `4*column+row`, for columns 0–4 and rows 0–3.
Horizontal edge `4*cut+row` has cut 0–5: cut 0 is a left half-edge, cut 5 a right
half-edge, and other cuts join adjacent columns. Vertical edge `24+3*column+row`
joins rows `row,row+1`, with row 0–2. Only left half-edges carry logical bit 1.
`input/graph.json` gives the complete incidence. The fixed graph has 39 edges,
20 detectors, maximum detector degree four, and logical distance six. It has no
parallel edges or edges with zero detector incidence. No graph changes are allowed.

For calibrated independent Bernoulli probabilities `q`, enumerate configurations
`x` with the submitted detector syndrome. Let `J_l` be the unconditional sum of
their probabilities in logical class `l`, and let

```
C_l = min(sum(x_e * log((1-q_e)/q_e))) over that syndrome and logical class.
```

Fix `physical = int(C_1 < C_0)` at nominal rates, with ties assigned 0. Everywhere
else report `gap=C_(1-physical)-C_physical`, posterior
`J_(1-physical)/(J_0+J_1)`, log odds `log(J_(1-physical)/J_physical)`, and syndrome
mass `J_0+J_1`. The physical class is never reselected under calibration. Positive
certified gaps imply it remains the physical MAP class throughout the domain.

## Calibration domain

All three families below are required. Nominal rate constraints apply to `p`,
not to calibrated `q`. Every calibrated rate remains positive and below 0.5.

**Global:** `q_e(alpha)=alpha*p_e`, for the entire interval [0.95,1.05]. Its targets
are gap 1.08, opposite posterior 0.85, and syndrome probability 0.0000175.

**Inherited spatial:** Use all nonconstant sign vectors of length four (rows)
or five (columns) whose first sign is +1. There are 7+15=22 vectors. Each defines
a detector field `u(column,row)` equal to the selected row or column sign.
Set `raw_e` to the average of `u` over that edge's detector endpoints; a half-edge
uses its sole endpoint. For every field compute

```
center = sum(p_e * raw_e) / sum(p_e)
d_e = (raw_e-center) / max_e(abs(raw_e-center))
q_e(t) = background * p_e * (1+t*d_e)
```

Use both backgrounds 0.95 and 1.05, each with the entire interval `t∈[-0.05,0.05]`.
This gives 44 inherited local paths.

**Orientation-conditioned extension:** Set `eta_e=+1` on all horizontal edges,
including both boundaries, and `eta_e=-1` on vertical edges. Use exactly these
43 detector fields, with no hidden or random additions:

- The constant +1 field.
- All 7 canonical row fields and all 15 canonical column fields just defined.
- For each of the 20 pairs `(selected_row,selected_column)`, the product field
  `(1-2*[row=selected_row])*(1-2*[column=selected_column])`. Thus the two selected
  lanes have negative sign except their positive intersection; other detectors
  have positive sign.

Now set `raw_e = eta_e * average_of_endpoint_fields`, then center and normalize
exactly as above. Use both backgrounds and the same entire amplitude interval.
This adds 86 paths. Both amplitude signs are included, so complementary detector
fields need not be separately enumerated. All locations of the crossed lanes
are included; the domain is closed under horizontal and vertical reflections.

Both local families have the same unchanged targets: gap 0.85, opposite posterior
0.845, and syndrome probability 0.0000175. Since `sum(p_e*d_e)=0` and `|d_e|≤1`,
all local paths preserve the expected total error count of their background and
change each rate by at most 5%. Orientation-dependent calibration is a new
uncertainty direction, not an increase in the allowed perturbation magnitude.

There are 1+44+86=131 lines. The two background values do **not** imply a claim
about intermediate backgrounds when local amplitude is nonzero. Neither arbitrary
simultaneous mode combinations nor the full detector/edge calibration box are
certified. The product fields are the stated finite family, not a full 2D box.

## Fixed sufficient certificates

All anchor locations and the numerical guard `1e-10` are fixed before attempts.
Every anchor is evaluated by exhaustive nonnegative summation and min-plus
inference, not Monte Carlo, low-weight truncation, or matching-package behavior.
“Exact” means exhaustive combinatorial inference in binary64, not rational arithmetic.

The inherited global and spatial certificates are unchanged. Global anchors are
0.95,0.955,…,1.05, with

```
D_global = 39/0.95 + sum(p_e/(1-1.05*p_e)).
```

Inherited local anchors are -0.05,-0.048,…,0.05. For direction `d` and background `b`,

```
D_local = sum(abs(d_e)/((1-0.05*abs(d_e))*(1-b*p_e*(1+0.05*abs(d_e))))).
```

Let `radius` be half the adjacent anchor spacing and `A=D*radius+1e-10`.
The lower bounds are the minimum anchor gap minus `A`, the minimum anchor log
odds minus `A`, and the minimum anchor syndrome mass times `exp(-A)`.

New orientation paths use 41 anchors -0.05,-0.0475,…,0.05 and an interval-specific
endpoint-cone certificate. Write `q_e(t)=a_e+t*v_e`. On each adjacent interval
`[left,right]`, let `qmin_e` and `qmax_e` be the min and max of its two endpoint
rates, and compute

```
D_interval = sum(abs(v_e)/(qmin_e*(1-qmax_e))).
lower(f,interval) = min(f(left), f(right),
                        (f(left)+f(right)-D_interval*(right-left))/2) - 1e-10.
```

Apply this to gap, log odds, and log syndrome mass separately, then take the
minimum over all adjacent intervals. Convert log odds by the sigmoid and log
mass by exponentiation. These are the required new-path certificate bounds.
Bounds missing targets are failures even if no sampled point violates a target;
the report explicitly distinguishes actual anchor failures from certificate-only
failures. No optimization-dependent hidden refinement changes acceptance.

**Why the continuous bound holds:** For one edge, the present and absent
log-probability slopes are `v/q` and `-v/(1-q)`. They have opposite signs and
their difference has magnitude `abs(v)/(q*(1-q))`. Therefore configuration
log-probability slopes occupy an interval containing zero, of width at most
`D_interval`. Log derivatives of nonnegative sums are weighted averages of those
slopes. Thus both log odds and log syndrome mass are `D_interval`-Lipschitz.
An edge cost has slope `-v/(q*(1-q))`; all subset-cost slopes occupy one interval
of the same width. The difference of class minima is `D_interval`-Lipschitz,
including at min-cost kinks. There is no extra factor of two.

From either endpoint, the value of a Lipschitz function is at least its endpoint
value minus distance times `D_interval`. The minimum of the maximum of these two
cones is the expression above (with the endpoint minima making it conservative
even if rounded endpoint values are slightly inconsistent). This proves coverage
of every point, rather than incorrectly inferring extrema from corners. The
inherited derivative bounds follow from the same slope-range argument.

## Scores, checker, and resources

A path score is the nonnegative part of the minimum of certified gap/target gap,
certified log odds/target log odds, and certified mass/target mass. `core_score`
is the minimum across all paths. Passing requires every certificate to meet its
target. `inherited_generation_two_score` uses just the first 45 paths;
`extension_score` uses the 86 new paths. `worst_scale_score` is the minimum
normalized anchor score before any certificate allowance, diagnostic only.
`nominal_score` is the original global score. Runtime and resource scores are 1
for valid artifacts and 0 for invalid artifacts; speed is not rewarded.

`workspace/check.py` is the generation-three entry point. It exposes
`load_submission`, `validate`, `frontier`, `calibrations`, and `check`.
`calibrations(data)` returns every probability matrix and certificate parameter.
`frontier` returns both unconditional class masses and both minimum costs.
`inherited.py` and `core.py` support the unchanged prior requirements; they are
not alternative acceptance checkers. `--summary-only` suppresses detailed groups
on stdout, while `--output` preserves the full result.

There are exactly 5,791 inference points: 21+44*51+86*41. Trusted evaluation
independently constructs this schedule and uses the full 2^21 syndrome/logical
state space, with a reversible binary basis change. It does not import the
public frontier checker or consult any witness. Its fixed work is independent
of the submitted rates or syndrome. Only JSON is submitted; no untrusted code runs.

Construction has a 3,600-second wall budget. Artifact evaluation separately has
a nominal 900-second allowance, one native CPU thread, and 1 GiB. Shared-host
contention is not a scientific failure: no internal wall watchdog invalidates
an artifact. Measured CPU time, wall time, and peak RSS are reported independently.

## Scientific scope and provenance

Both generation-two fresh attempts passed independently; the higher-scoring
actual v1 artifact is the supplied baseline. Position-independent patches and
simple convex row/column mixtures did not break it. The present orientation and
crossed-lane extension exposes genuine gap/posterior failures at the same rate
budget and targets. It probes whether entropy-driven logical disagreement is
stable when calibration distinguishes different edge orientations and positions.
Achievability is unknown, not verified or assumed impossible.

Higgott and Gidney, *Sparse Blossom*, arXiv:2303.15933v2, sections 2.1–2.3, supplies
the physical-MAP/logical-ML distinction. Relevant primary context includes Bravyi,
Suchara and Vargo, arXiv:1405.4883, and Smith, Brown and Bartlett, DOI
`10.1038/s42005-024-01883-4`. The confidence inference tested here is not a theorem
attributed to those papers. Neither exact matching correctness nor any claimed
decoding throughput is challenged by this task.

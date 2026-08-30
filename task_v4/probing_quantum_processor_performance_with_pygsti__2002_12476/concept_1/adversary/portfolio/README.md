# Private optimizer evidence

This directory is privileged generation-time work, not a fresh-agent attempt.
No fresh submission, attempt workspace, or runner was inspected or invoked.
All writes are confined to this directory; participant assets and the frozen
evaluator and targets were not modified.

## Outcome

`design.json` is a legal passing construction for the fixed targets. Its exact
frozen-evaluator result is in `evaluator_score.json`:

- Overall A-risk reduction: **0.6590426041779536**.
- Worst-family reduction: **0.6134571553398454** (anisotropic).
- Mean risk: **4.5017376961541355**, versus **13.203226418656973** nominal baseline.
- Execution cost: **1,599,680 / 1,600,000** ticks; **24** distinct circuits.
- Every batch count is integral and at most 48; each batch contains 64 shots.
- `valid=true`, `passed=true`; neither fixed target was changed.

Solvability is demonstrated by this separate privileged construction. Whether
the concept is hard remains the main session's fresh-agent decision; this is
not evidence that an isolated agent solved it. If that attempt fails, this
construction supports `hard_verified_achievable` rather than an open candidate.

## Independent broad validation

After fixing the design, `optimize.py --audit-only --audit-per-family 500`
sampled 3,000 new operating points using seed 982734005 and the disclosed
sampler. These draws were not used to select or optimize the design.

| Regime | A-risk reduction |
| --- | ---: |
| near_nominal | 0.6783790848645898 |
| long_coherence | 0.6718583582623099 |
| detuned | 0.6691984661097847 |
| anisotropic | 0.5556937744861220 |
| readout | 0.6771248619216883 |
| mixed | 0.5476509555360256 |

Overall reduction is **0.6262623612257789**; worst-family reduction is
**0.5476509555360256**. Mean baseline and candidate risks are 12.898187482872721
and 4.820538134316065. Both original aggregate targets pass again.
The paired, stratified 2,000-bootstrap 95% interval for overall reduction is
[0.6220181635913385, 0.6302843900318805]. Family intervals are retained in the
machine-readable result; even the lowest interval endpoint exceeds 0.53.

The candidate improves 2,996 of 3,000 individual points. Four mixed-regime
points are worse than the nominal baseline; the worst ratio is
1.3392838573387265. Their physical parameter vectors and risks are saved in
`broad_space_score.json`, and all draw parameters and paired risks are saved in
`broad_space.npz`. This is an aggregate-design success, not a uniform guarantee
over every physical parameter point.

## Search record

`search.jsonl` records private search progress and all reported improvements.
The search uses fixed-support SLSQP with analytic A-risk gradients, a capped
multiplicative continuous relaxation, backward circuit removal, add/drop
support exchanges, integer shot exchanges, worst-family reweighting, and a
randomized family-weight portfolio. The corrected continuous relaxation
reaches a normalized mean-risk objective near 0.316824 before the 24-circuit
support restriction is imposed; this number is not an optimality certificate.

The first exploratory relaxation had a numerical normalization defect when
weights approached zero. It was detected from its invalid allocation sum and
replaced with bracketed capped normalization; its relaxation numbers should
not be treated as feasible designs or bounds. The local integer designs from
that exploratory run were separately checked by the unchanged evaluator.
The corrected run reached a passing design through continuous pruning in
about 18 seconds and the final retained score through subsequent exchanges.
The private weight-portfolio restarts are not champion-ratchet generations.
There were **zero** fresh-agent or champion-ratchet generations in this sidecar.

The searches were explicitly stopped after achievability was established and
scores stabilized. Sandbox PID isolation required a narrowly scoped host-side
stop of the two private optimizer command lines; no fresh-agent process was
targeted. The final audit and saved artifacts are independent of search-process
termination.

## Reproduction

Run from `concept_1/` using the installed NumPy/SciPy interpreter:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python adversary/portfolio/optimize.py --seconds 300 --audit-per-family 500
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python adversary/portfolio/validate.py
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python evaluator/evaluate.py --submission adversary/portfolio/design.json --output adversary/portfolio/evaluator_score.json
```

The optimizer warm-starts from an existing private `design.json` when present.
To retain the design and repeat only the independent sampler audit:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python adversary/portfolio/optimize.py --audit-only --audit-per-family 500
```

`validate.py` checks the legal integer design, reproduces the evaluator score,
rebuilds selected hidden Fisher features from the disclosed model, compares
analytic gradients with finite differences, and records SHA-256 hashes of the
design and frozen assets in `numerical_audit.json`.

## Separate loss follow-up

`LOSS.md` and `loss_audit.json` document the additional no-reallocation,
leave-one-selected-circuit-out diagnostic. On the same 3,000 broad draws, mean
inflation over the 24 possible losses is 1.222372x; the most harmful circuit
loss doubles population mean risk, and the largest individual inflation is
21.268719x. Seven of the 24 losses fail the original aggregate score thresholds.
This does not change the original objective or invalidate the intact design.
The principal mechanisms concern redundant angle sensing, readout calibration,
and decay-rate separation. The important worst-point witnesses pass derivative
step-size and direct-inversion versus Sherman-Morrison checks.

# Frozen baseline-improvement objective

For each case, `B` is the independently recomputed energy of its **provided
initial field**. `W < B` is the energy of a separately stored private lower-energy
witness. Each frozen reference gap is at least 0.5. Witnesses are feasible
attained upper bounds, not global minima or certificates; beating one is welcome.
References and thresholds do not change in response to submissions.

For checked output energy `E`, the score is `clip((B-E)/(B-W), 0, 1)`.
There are **three cases in one collective-fluxoid family**. Its arithmetic mean
is both `core_score` and `worst_family_score`; all cases count. Invalid or missing
cases score zero and independently force failure. The general aggregation is an
equal case mean within each family and equal family mean for the core.

`passed` requires all of:

- Three valid, finite complex outputs within all resource limits.
- Gradient RMS `sqrt(sum_active(abs(g)**2)/(2*N)) <= 0.002` on each case.
- No regression: `E <= B + 1e-8*max(1,abs(B))` on each case.
- `core_score >= 0.65` and `worst_family_score >= 0.45`.

The 0.65 core requirement is binding with one family; the 0.45 worst-family
threshold is retained explicitly. Returning the supplied initial field is a
reproducible zero-score feasible baseline, independent of stochastic search time.

`runtime_score = mean(max(0,1-trusted_wall_seconds/60))`, with invalid cases
contributing zero. It is separate from the energy score and cannot offset a
quality failure. Timings come from the trusted execution harness, never NPZ or
submission stdout. Startup and I/O count. Reports give core, worst family,
runtime score, validity, `passed`, and explicit reasons.

The target is frozen before the next fresh attempt. Expensive witness
construction and measured resource-bounded executable performance are distinct
evidence; neither implies a true ground-state claim or universal solvability.

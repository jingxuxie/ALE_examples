# Frozen baseline-improvement objective

For each hidden case, `B` is the independently recomputed energy of the frozen
public baseline field. `W < B` is the independently recomputed energy of a
privately constructed, explicitly stored witness field. Witnesses are attained
upper bounds on the unknown global minimum, not exact minima or certificates.
Every reference gap `B-W` must be at least 0.5 before the benchmark is frozen.
No energy references are updated in response to a submission.

For independently checked output energy `E`, raw gap closure is `(B-E)/(B-W)`.
The case score is `clip(raw_gap_closure, 0, 1)`. Compute an arithmetic mean within
the single perforated-grain family, which contains three cases. `core_score`
and `worst_family_score` therefore coincide. All three cases count, including
invalid/missing cases with score zero. Invalid cases still force failure.

`passed` requires all of:

- Three valid, finite complex outputs within all resource limits.
- Independent gradient RMS `sqrt(sum(|g|**2)/(2*N)) <= 0.002` on each case.
- No energy regression: `E <= B + 1e-8*max(1,abs(B))` on every case.
- `core_score >= 0.65` and `worst_family_score >= 0.45`.

`runtime_score = mean(max(0,1-wall_seconds/60))` over all three cases, with invalid
cases contributing zero. Wall time is measured by the trusted sandbox helper,
includes process launch and I/O, and is never taken from solver stdout or NPZ.
Runtime is reported separately, not multiplied into the energy score. Lower
runtime breaks ties only when energy scores are equal. A failed run always has
`passed: false` and explicit case/aggregate reasons.

The benchmark baseline is the exact supplied `initial_real + 1j*initial_imag`
field. Returning it has zero gap closure and is independent of optimizer timing.
`baseline/solve.py` does exactly this; `baseline/champion.py` is a stronger
previous solver supplied as an additional starting point, not a moving energy
reference. The current inputs are adversarially selected, not an IID sample.

Thresholds and reference fields were frozen before the new fresh-agent launch.
There is no claim that an in-budget algorithm must reach a witness;
builder calibration separately reports expensive-witness attainability and
measured in-budget solver performance.

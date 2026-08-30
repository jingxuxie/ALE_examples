# Generation-1 sidecar: calibration-drift evidence

## Handoff

The original fresh submission **still passes the original frozen task at 100/100**;
this sidecar does not revoke or modify that result. All 23 files were copied
byte-for-byte from `attempts/frozen_v_1/` to `champions/generation_1/`.
The participant, evaluator, frozen target, original generation, and original
score were not edited. No fresh model or delegated agent was launched.

**Proposed next-generation calibration scale: ±0.002 radians per knot.**
It is the smallest tested scale with substantive failures of the new champion;
all 90 drift directions at each smaller scale through ±0.001 passed all five
original perturbations. Keep error ≥0.15 and spread ≤0.008 unchanged.

## Bounded experiment

- 902 cases, 4510 actual 12-site physical waveforms, four CPU workers with one BLAS thread each.
- Sweep runtime: 648.27 seconds (10.80 minutes), excluding the final representative-case audits.
- At each scale and for each witness: all 64 six-dimensional sign corners, 12 fixed-seed uniform-cube random directions, and 14 structured directions (12 single-knot signs and two alternating patterns).
- Each direction is added to the six control knots before the unchanged original five offset/tilt families are formed. The two unchanged baselines are also recomputed.
- Every case is valid: True. Nominal knot bounds, all actual pulse bounds, slew, pulse order, ZZ sign, site order, observable, and chi caps use the frozen protocol.
- Exact evolution, actual MPS evolution, and observable measurement use the trusted snapshot and independent bit-pair oracle, not any fresh submission code.

## Failure counts

A case fails if any of its five families fails. Random plus structured counts
are a finite diagnostic sample, not an estimated real-world failure probability.

| Knot drift | Fresh corners | Builder corners | Fresh other | Builder other | Fresh max corner spread | Builder max corner spread |
|---|---:|---:|---:|---:|---:|---:|
| 0.0001 | 0/64 | 4/64 | 0/26 | 0/26 | 0.005806789 | 0.008151137 |
| 0.00025 | 0/64 | 50/64 | 0/26 | 9/26 | 0.006061943 | 0.013885500 |
| 0.0005 | 0/64 | 32/64 | 0/26 | 10/26 | 0.006293620 | 0.014165429 |
| 0.001 | 0/64 | 8/64 | 0/26 | 9/26 | 0.006815259 | 0.013287424 |
| 0.002 | 11/64 | 17/64 | 0/26 | 3/26 | 0.008939541 | 0.009446172 |

All observed failures are **spread-only**. Across the complete sweep the
minimum chi-16 exact error is 0.155154235571, above 0.15. Calibration drift
breaks agreement of the finite-bond estimates, not the underlying large bias.

## Strongest fresh failure

- Drift: `0.002 * [-1,+1,+1,+1,+1,-1]`, a genuinely nonuniform calibration pattern.
- Original family: `tilt_minus`.
- Exact ZZ: **0.397981924175**.
- MPS chi 4, 8, 16: **0.568020691669, 0.567776132376, 0.558836591826**.
- Spread: **0.008939540550**; exact error: **0.160854667651**.
- The unchanged checker accepts the waveform as valid and rejects its convergence requirement, scoring worst-family **89.490058**.
- Replay artifact: `adversary/generation_1/failures/fresh_strongest_failure/witness.json`; adjacent files contain the full frozen evaluation and independent audit.

At ±0.002, all 11 failing fresh corners are nonuniform: **3/20 zero-mean
balanced corners** and **8/42 unbalanced mixed corners** fail. Both uniform
corners pass. Thus the new failure is not merely a larger common-mode field
offset disguised as six-dimensional drift. The fresh random and structured
samples still pass at this scale, emphasizing the value of joint corners.

## Failure mechanisms

These are measured sensitivity clusters, not a claim of a new analytic theorem.

1. **Fresh witness: chi-8 versus chi-16 spread margin.** All 14 failing families
   use the chi-8/16 pair, with chi 8 having the larger change from the matched
   original family. In the strongest case, exact ZZ changes by +0.004740779077;
   chi-4, chi-8, and chi-16 change by +0.002325890096, +0.006877351750, and
   +0.003307780075. The residual chi-8/16 spread grows beyond 0.008 while the
   chi-16 bias remains well above 0.15.
2. **Builder witness: primarily chi-4 truncation sensitivity.** Of its 227 failing
   families, 213 are chi-4/8 spread failures dominated by chi-4 change, four are
   chi-4/8 failures dominated by chi 8, and ten are chi-8/16 failures dominated
   by chi 8. The earliest failing scale is ±0.0001. In that representative
   trajectory, the final exact change is only -0.000005847492, but chi 4 changes
   by +0.003281052270; its difference exceeds 0.001 starting at layer 15.
   Chi-8 and chi-16 changes remain below 0.00005 at the final layer. This is
   finite-bond nonlinear evolution sensitivity, not evidence of an oracle bug
   or a claim that chi-8 Schmidt degeneracy caused these chi-4-dominated failures.
3. **No physics-invalid or exact-error-floor cluster.** All waveforms are legal,
   all biases remain ≥0.15, and independent recomputation reproduces the faults.

The builder's strongest sampled failure is a random direction at ±0.0005
(`random_09`, family `tilt_minus`): spread
**0.014376457620**, error **0.167744311524**, worst-family score
**55.646531**. Its replay artifact is
`adversary/generation_1/failures/builder_strongest_failure/witness.json`.

## Trust and limitations

The selected smallest-scale and strongest failures for both witnesses were
regraded with the unchanged CLI and checked against a second exact-statevector
implementation, independent observable computation, full-rank chi=64, and
`gesvd` versus `gesdd`. All checks pass; the largest numerical discrepancy is
1.49e-10, many orders below the observed violations.
The fresh strongest failure's SVD-driver difference is
7.33e-15.
The sweep and frozen-checker metrics agree within the audit tolerance.
All frozen manifest hashes still match, and the copied champion is still
byte-identical. `final_audit.json` records these facts.

The builder failure rate is nonmonotonic in drift radius, and its strongest
failure is an interior random point at ±0.0005, not an outer ±0.002 corner.
**Corners alone do not certify the continuous calibration box.** The proposed
requirement must be described as a finite-suite robustness requirement. If the
next generation claims more than that, include nested-radius and interior
checks explicitly rather than assuming extremal behavior of this nonlinear
MPS evolution. No continuous-box certificate has been established.

## Concrete next-generation proposal

1. Keep the physical circuit, observable, six controls, depth/slew bounds,
   chi caps, error ≥0.15, and spread ≤0.008 unchanged.
2. Form drift directions `{0} union {-1,+1}^6` at **epsilon=0.002**.
3. Cross every drift with the original five global offset/tilt families:
   **325 actual waveforms** per candidate. Require success on every waveform.
   Preserve the nominal core score; take worst-family score over all 325.
4. Keep nominal knot bounds; validate physical pulse bounds and slew after both
   perturbations. Combined worst-case pulse displacement is 0.004 radians,
   because the original and new errors can add; this must be stated publicly.
5. Keep resource/depth scoring unchanged. Full grading costs roughly 65 times
   the original five-family evaluation; budget about 100–200 serial seconds
   at these small depths, or explicitly bounded parallel evaluation. This is
   a projection, not a new measured runtime guarantee.
6. Label this **hard_open_candidate**, not a known-feasible frozen replacement.
   Neither tested witness passes: fresh would have worst score 89.490058,
   builder 84.690387. Builder C should search for a passing witness and assess
   feasibility before freezing. Fresh survives every tested scale through
   0.001, so an active-corner search warm-started there is a reasonable next
   experiment; no such optimization was performed in this bounded sidecar.

The 0.002 scale comes from a changed calibration model with independently
perturbed knots, at the same numerical scale as the existing global error.
It does not arbitrarily tighten the scoring thresholds. It is the smallest
**tested** radius with substantive fresh failures, not an estimate of the exact
critical radius. The random seed and suite were fixed before the sweep.
`proposal.json` is advisory only; nothing in the original generation is ratcheted.

## Evidence and reproduction

- `preservation.json`: source-to-champion file hashes for all 23 fresh files.
- `sweep_plan.json`, `sweep.jsonl`, `summary.json`: complete design and results.
- `failure_clusters.json`: matched-family estimate shifts and calibration-shape counts.
- `failures/`: replayable witnesses, frozen evaluations, independent audits, and selected per-layer trajectories.
- `final_audit.json`, `proposal.json`: trust checks and advisory successor target.

From the concept directory:

```bash
python adversary/generation_1/drift_audit.py --workers 4
python adversary/generation_1/analyze.py
python -I evaluator/evaluate.py --submission adversary/generation_1/failures/fresh_strongest_failure --output adversary/generation_1/replay.json
```

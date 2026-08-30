# Private adversary handoff — August 28, 2026

## Conclusion

**No broad, statistically clear within-law failure is established against a
final champion.** The active snapshot is near the threshold on multiband
continua. A scientifically meaningful low-information conditional subgroup
shows a reproducible point-score weakness, but its bootstrap interval touches
85 and the live solver changed during the experiment. Do not manufacture a
new threshold or claim this rejects the final submission. Parent must confirm
the official pass and retest the saved independent fixtures with final code.

All snapshots, code, weights, labels, predictions and fixtures remain private.
No participant, target, official split or parent status was modified. Any
future authorized public ratchet must retain the weak NNLS baseline and draw
new independent public training/validation data, not copy these fixtures or
the previous solver/source/model pool. See `PRIVATE_ONLY.md`.

## Counts and resources

- 2,304 independent spectra generated from six new seeds using the exact
  existing public spectral, beta, Gaussian-noise and covariance law.
- Three complete IID batches: 288 scored cases, 48 per family, across three
  seeds. A fourth 96-case batch hit the 120-second wall limit and has no
  scientific score; timing failure is not treated as an inference failure.
- 64 additional independent confirmation predictions from two new seeds:
  16 four/five-component multibands, 24 Hubbard metals, and 24 hot/noisy
  multibands. Five generation seeds contribute scored cases; 352 scored total.
- Search, preparation and confirmation elapsed compute wall time totals
  **532.191680 seconds**, within the approximately ten-minute compute budget.
  Shell startup/approval latency is not included in this compute figure.
- Every predictor invocation uses strict whitelist-only bubblewrap. Only
  features, original public assets and the immutable snapshot are mounted.
  Labels and parameter traces are scored in the trusted process afterward.
- Initial calls used the runner's default first CPU. Confirmation used the
  second allowed CPU, still exactly one core, to avoid official-run contention.
  Confirmation took 56.357003 seconds for 64 cases. Neither timing profile
  establishes official 192-case runtime for the changed final solver.

## IID discovery results

| Seed index | Cases | Core | Worst family | Wall seconds |
| --- | ---: | ---: | ---: | ---: |
| 0 | 96 | 92.336557 | 85.615638 | 111.588972 |
| 1 | 96 | 92.197838 | 83.133611 | 104.746981 |
| 2 | 96 | 92.554475 | 85.987181 | 111.051043 |

Multiband continua are worst in all three batches. Pooled multiband score is
84.90263 over 48 cases; this is a marginal weakness, not a decisive broad
failure. The original four-discovery/four-confirmation plan was amended after
the fourth discovery timeout, before seeing any confirmation prediction.
The resource amendment is explicit in
`bounded_confirmation/protocol_amendment.json`; no scientific target changes.

## Independent confirmation

| Cohort | Cases | Score | Bootstrap 95% interval | 80% interval coverage |
| --- | ---: | ---: | --- | ---: |
| Primary: four/five-component multibands | 16 | 85.715082 | [82.508527, 88.771266] | 100% |
| Calibration: Hubbard metal | 24 | 91.822306 | [87.778780, 95.185754] | 75% |
| Secondary: low-information multibands | 24 | 82.723233 | [80.247299, 85.096557] | 95.8333% |

Primary selection retained the lowest-discovery-score eligible physical group
with at least 16 cases. It does not independently fail the 85 comparison.
The secondary low-information group was prelisted physically, but had only
11 discovery cases, below primary eligibility; it is explicitly a secondary
exploratory hypothesis with fresh independent confirmation, not a hidden
replacement of the primary selection rule.

The low-information predicate is **family 5, beta <=16, and
sqrt(trace(covariance)/56) >=2e-4**. All other spectral and observation draws
retain the original public law. Confirmation chooses the first qualifying
rows from an independent pool without using prediction errors; all selected
rows are retained. This is hot/noisy multiband analytic continuation, not
arbitrary metadata or a new parameter range.

For this subgroup, mean normalized W1 is 0.00593490, low-mass MAE 0.00459214,
band total-variation error 0.01703694 and gap10 MAE 0.03051830. Median forward
chi-square is 50.18472 for 56 observations. Seven of 24 cases have per-case
score below 80 while forward chi-square remains below 90: spectral errors
remain despite fitting the noisy imaginary-time data reasonably well.
This illustrates ill-conditioned reconstruction, not an impossibility proof.

Hubbard-metal nominal 80% coverage is 75% on confirmation, with Wilson 95%
interval [55.10%,88.00%]. It does **not** establish systematic undercoverage.
The Mott and some multiband spectra have exact zero low-mass atoms; naive
quantile-CDF equality or demanding exactly 80% coverage at those atoms is not
a valid failure argument. Proper pinball scoring remains unchanged.

## Identity and retained artifacts

Snapshot solve SHA256:
`c33570fc90cebf4cf7c39f385d1c527c16f1988b055f50e4fead917982c748c1`.
Observed live solve SHA256 at confirmation:
`b75232b6882b7c79d3ba8ff2b3ceb8e94a122864b2d855f452740d991dbfd80e`.
`solve.py` and `multiband.py` changed. Do not attribute these results to final
code without retesting. No source/model artifacts are public candidates.

- `snapshot_manifest.json`: immutable source/model hashes and frozen-asset hashes.
- `search_report.json`: IID aggregates, groups, timeout and source-change record.
- `data/seed_*/`: exact generation manifests, NPZ features/labels, parameter
  traces and completed prediction/row-analysis reports.
- `bounded_confirmation/report.json`: independent confirmation scores/resources.
- `bounded_confirmation/{primary_fixture,calibration_fixture,low_information_stress_fixture}/`:
  frozen input, labels, snapshot predictions, parameter traces and hash manifests.
- `retest.py`: private isolated final-code fixture comparison, not an official
  pass/fail evaluator or a new public target.

From the paper-task directory, outside the nested sandbox:

```
python3 -B concept_3/adversary/champion_v1/retest.py --submission FINAL_DIR --fixture concept_3/adversary/champion_v1/bounded_confirmation/low_information_stress_fixture --output concept_3/adversary/champion_v1/final_low_information_report.json
```

Run official timing separately from other pinned-core tests. Parent owns
official scoring, final champion identity, status, and any ratchet decision.

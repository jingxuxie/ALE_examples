# Final-target achievability demonstrated

The unchanged official evaluator accepts the complete three-family artifact:
`valid=true`, `passed=true`, `core_score=1.0`.

- Artifact: `champions/private_achievability.json`.
- First official report: `champions/private_achievability_report.json`.
- Independent official rerun: `champions/private_achievability_recheck.json`.
- Reproducibility and arithmetic audit: `adversary/achievability/validation.json`.
- Seeds/config/input snapshots: `adversary/achievability/run_20260828T153310Z_161/`.
- Artifact SHA-256: `f022f5d74b0ed657bdb7ea7da0ef649cb380c78a12a0e6c7b9e802b8451f5d85`.

## Grid certificate

| Direction | Single minimum | Double minimum | Single mean | Double mean |
|---|---:|---:|---:|---:|
| Forward | 9 | 7 | 14.233333333333333 | 14.873684210526315 |
| Inverse | 9 | 7 | 14.233333333333333 | 14.780116959064328 |

Ladder and bridge reuse the existing privately verified passing designs. Exact
independent integer propagation agrees with the official kernel for all 8,658
specified input/direction cases across the three families. Replaying the winning
worker from its committed seed reproduces its circuit exactly.

## Runtime and interpretation

The new four-worker search stopped immediately after finding feasibility:
0.749597 seconds including setup and the first official evaluation; recorded
aggregate search-worker CPU time was 0.151692 seconds. The winning worker used
36 candidate evaluations. These numbers exclude the substantial earlier private
calibration that produced the near-feasible warm start. They are not a fresh
agent timing or a claim about fresh-run difficulty.

No fresh-attempt files were read, no information was sent to the fresh solver,
and no participant/evaluator files were modified. Frozen source/specification
hashes were checked before and after. Root `status.json` was deliberately not
edited because it is outside this follow-up's exclusive write scope; the main
process may use this certificate to upgrade the feasibility assessment.

From the concept root, rerun the frozen official evaluator without bytecode writes:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission champions/private_achievability.json --output champions/private_achievability_recheck.json
```

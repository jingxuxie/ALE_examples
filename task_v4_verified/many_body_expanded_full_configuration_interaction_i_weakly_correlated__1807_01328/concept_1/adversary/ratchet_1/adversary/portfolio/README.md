# Private bounded E2 achievability portfolio

This directory is privileged generation-only material. Do not expose it to the
fresh solver. No frozen participant/evaluator/target/data/status was changed,
no fresh-run output was inspected, and no fresh agent was launched. Main retains
control of the ongoing attempt and all frozen/status assets.

## Best measured policy

The exact tested submission is `candidate_a/` (eight files). It starts from the
authorized original E1 champion helpers and original neural weights. No private
core coefficients, case identifiers, hidden energy tables, witness files, or
new lookup-trained network are included in the submission. Its only model-file
loads at runtime are the original local `network4.npz` and `network5.npz`.
Unused generation utilities inherited from original helpers are not invoked by
the solution entrypoint. Strict bubblewrap mounts only this submission and the
frozen public participant assets; private portfolio/evaluator data are absent.

After obtaining the 56 triples, the policy detects a seven-virtual region whose
triple increments are small relative to the rest, using observed values only.
In that case it derives a covariance scale from observed pair increments and
singleton energies, requests a six-virtual aggregate experiment, and allocates
the remaining budget adaptively. It bypasses the old conditional physical fit
for those cases. Other cases retain the original policy. The detector is
permutation-equivariant apart from ordinary numerical tie-breaking and never
uses a fixed hidden orbital slot or a case identifier. Constants are generic
acquisition hyperparameters selected by private offline tuning, not physical
coefficients or per-case answers. The policy does not cache estimates by model.

## Actual strict-sandbox results

All values below are complete 120-system runs with a single persistent policy,
unchanged CPU120/query160/2 GiB limits, and the unchanged E2 PID-1 descendant
CPU/RSS guard. No threshold was tightened or relaxed. Each run used cost160
at most; all passed the original overall10/worst25 microhartree targets.

| Run | Overall RMSE (microhartree) | Worst-stratum RMSE (microhartree) | CPU (s) | Wall (s) |
| --- | ---: | ---: | ---: | ---: |
| Instrumented frozen-suite run | 7.801097 | 14.833027 | 64.084334 | 116.446053 |
| Actual unchanged frozen evaluator CLI | 7.801097 | 14.833027 | 59.058784 | 77.583016 |
| Independent diversified holdout | 6.206214 | 11.397722 | 83.060694 | 106.852350 |

The instrumented runner imports the unchanged frozen `sandbox_command`,
`limits`, `trusted_protocol.run_policy`, and `summarize`; it additionally saves
actual stderr query traces. The actual evaluator CLI independently confirms
the frozen-suite result. An external portfolio deadline can stop incomplete
runs early; it never extends the E2 CPU/query/memory/accuracy allowances. All
reported runs completed well before that deadline and the official wall600.

`candidate_a_official_score.json` is the canonical fixed-E2 pass certificate.
`candidate_a_fixed_score.json`, `candidate_a_holdout_score.json`, and their
worker logs contain aggregate resource evidence and actual query traces.
`query_evidence.json` verifies the fixed-suite trace costs against trusted
records: 20 detected cases use 67 queries (56 triples, one six-virtual query,
ten quadruples); the other 100 use the original 82-query pattern. Both cost160.

## Holdout independence and limitations

The candidate code is unchanged between all runs. The holdout was generated
with a separate predeclared seed, without screening or retuning on its scores.
It contains 100 new ordinary draws and 20 newly diversified, randomly relabeled
conditioned stress systems. Both private seed neighborhoods use bounded
22-dimensional SVD near-null moves, independent coefficient noise, independently
varied diagonal-gauge descriptors, and new nontrivial added-site couplings.
All models satisfy the E2 coefficient/range/reference/gap domain. All 256
energies per system, independent Hamiltonian/eigenpair checks, and stress
permutation covariance are validated during generation.

Each holdout core's CAS2 vector differs from every tuning core: nearest-core
maximum-coordinate discrepancies range from 4.9673 to 34.9963 microhartree.
This rules out exact-core reuse in these comparisons. The holdout remains
conditioned and derived from two private seed neighborhoods, not independent
new witness discoveries or an IID population sample. The result is a concrete
observation-driven achievability example for fixed E2 with useful neighborhood
validation, not a universal guarantee over its broad continuous domain.

Detailed construction, diversity, and independence evidence are private in
`holdout/provenance.json`, `holdout/diagnostics.json`, and
`holdout/independence_check.json`. Offline screening results are explicitly
marked tuning diagnostics rather than official scores.

## Reproduction

From the task root, with an outer environment permitting strict bubblewrap:

```bash
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 concept_1/adversary/ratchet_1/evaluator/evaluate.py --submission concept_1/adversary/ratchet_1/adversary/portfolio/candidate_a --output /tmp/e2_private_candidate_recheck.json
```

No fresh-run or frozen status changes accompany this private certificate. See
`BEST.json` for immutable candidate hashes, measured scores, and the elapsed
portfolio budget record. Stop after this handoff; do not expand the portfolio
or tune against the holdout without new authorization.

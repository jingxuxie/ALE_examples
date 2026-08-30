# Provisional champion adversary protocol

This sidecar does not change participant files, the official hidden split,
thresholds, fresh submission files, or parent-owned status. The tested candidate
is a hash-verified private snapshot of the active `attempts/v_1` directory.
Official success and final-code identity must be confirmed by the parent before
any champion/ratchet conclusion. No agents are launched.

## Population and independence

Eight separately seeded batches contain 96 examples each, 16 per spectral
family. They use the exact original generator and complete public law, including
all original beta, noise, covariance, component and mixture distributions.
There is no altered noise scale, narrower-than-public peak, secret distribution
extension or dependence on opaque IDs. Seed construction is
`SeedSequence([20260828,871092,index])` for indices 0 through 7. None of the
official heldout labels or observations is reused. The generator is redirected
in memory to private sidecar output directories; original code/data are untouched.

Spectral RNG calls are traced without additional random draws, preserving the
law. `parameters.json` records the original draw order and values, together with
family and component count. Its row order matches the observation archive.
Full input, independent labels and predictions are retained for each seed.

Seeds 0–3 are discovery; seeds 4–7 are untouched confirmation. Predeclared groups
include each entire physical family, low-information multibands (beta <=16,
noise RMS >=2e-4), four/five-component multibands, high-energy-weight multibands
(outer-band mass >=0.5), narrow coherent peaks (width <=0.14) and hot/noisy
observations across families (beta <=12, noise RMS >=3e-4). Noise RMS is
sqrt(trace(covariance)/56), not a concealed latent feature. Only groups with
at least 16 discovery examples can be selected. The group with lowest discovery
score is fixed in `discovery_selection.json` before confirmation starts.

All confirmation examples matching that physical predicate are retained in
`confirmation_fixture/`, not just examples with poor predictions. Therefore a
confirmed conditional cluster is not produced by cherry-picking bad noise
realizations. The remaining confirmation groups are exploratory diagnostics.
The conditional fixture is not itself a balanced substitute for the official
heldout test or a newly frozen passing criterion.

## Security and resources

Every prediction executes with the existing strict whitelist bubblewrap runner,
one CPU and its normal 120-second invocation limit. Only a snapshot, the input
feature file, original public training/validation assets and scratch/output are
mounted. Private labels, parameter traces and generation/scoring code are not
mounted; scoring and diagnostics occur in the trusted parent process after
prediction completes. The search stops before another full invocation would
exceed its nominal 600-second sidecar budget. No GPU or network is used.

## Diagnostics and limitations

Scores and physical errors follow the unchanged public scoring definitions.
Coverage of the nominal 80% interval, empirical CDF at each reported quantile,
Wilson coverage intervals and bootstrap score intervals accompany every group.
Exact atoms at zero mass, especially in the Mott family, make naive quantile-CDF
equality inappropriate. A separately recorded secondary calibration protocol
selects a family on discovery only, excludes exact boundary atoms for nominal
coverage interpretation, and demands independent confirmation before claiming
systematic undercoverage. All-case coverage and excluded counts remain visible.
Bootstrap intervals describe row-sampling variability, not complete uncertainty
from model selection; independent confirmation is the primary safeguard.
Forward chi-square residuals distinguish obviously poor data fits from spectral
errors compatible with noisy imaginary-time observations. A row score below 80
with prediction chi-square below 90 is a diagnostic flag, not a new score gate
or a proof of information-theoretic impossibility.

Findings can be absent: a broad within-law failure is not assumed. Selected
stress groups and active-snapshot results must be described with their sample
counts and independent confirmation outcomes. No post-hoc threshold increase,
new distribution or assertion of impossible reconstruction follows automatically.

## Reproduction

Snapshot hashes and generator/input/label hashes are retained in manifests.
`search.py --prepare-only` creates the snapshot once and refuses replacement.
The bounded isolated experiment is:

```
python3 -B concept_3/adversary/champion_v1/search.py --budget-seconds 600
```

Run outside the nested sandbox so bubblewrap namespaces work. For a final-code
retest, use the existing `evaluator.runtime.execute_submission` on
`confirmation_fixture/input.npz`, mounting only original `participant/input`,
then score against the private fixture labels in the trusted process. Never
mount the fixture directory as public assets.

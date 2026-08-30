# Separate circuit-loss robustness audit

This is a follow-up diagnostic, **not part of the original objective**. The
passing design and original evaluator are unchanged. For each of the 24 selected
circuits, remove every one of its batches and recompute the same 14-parameter
information matrix and 12-parameter A-risk, with no shot reallocation. The two
readout parameters remain unknown unless explicitly fixed for diagnosis.

`loss_audit.json` contains every loss, family, physical worst-case parameter
vector, leading variance-increase directions, and numerical conditioning.
`loss_risks_frozen_hidden.npz` and `loss_risks_broad.npz` retain the full risk
arrays. All calculations use the same physical model and numerical ridge as
the frozen evaluator.

## Population summaries

Inflation is the ratio of post-loss mean risk to intact-design mean risk.
Mean inflation below averages that ratio over a uniformly selected one-circuit
loss; maximum inflation selects the most harmful one-circuit loss. These are
not claims about the real-world probability of acquisition failure.

| Dataset | Operating points | Mean inflation | Maximum inflation | Maximum individual inflation | Losses failing original score thresholds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen hidden | 60 | 1.2365753815000147 | 2.1131915986673830 | 5.280825826587039 | 6 / 24 |
| Independent broad | 3,000 | 1.2223716842347259 | 2.0100539094992680 | 21.268718863828045 | 7 / 24 |

The largest aggregate loss is candidate **151** on both datasets.
The intact broad risk is reproduced to 8.9e-16 absolute mean error, so this
audit is directly comparable to the saved no-loss broad validation.

## Broad family results

| Regime | Mean inflation over losses | Maximum mean-risk inflation | Worst circuit | Maximum pointwise inflation over all losses |
| --- | ---: | ---: | ---: | ---: |
| near_nominal | 1.209013 | 2.409401 | 151 | 3.100077 |
| long_coherence | 1.165798 | 1.653367 | 151 | 8.445640 |
| detuned | 1.225126 | 2.458615 | 151 | 3.340969 |
| anisotropic | 1.257685 | 2.189471 | 25 | 5.737615 |
| readout | 1.212917 | 2.414263 | 151 | 2.961242 |
| mixed | 1.229628 | 2.357872 | 59 | 21.268719 |

## Mechanism clusters

1. **Concentrated amplified angle information.** Candidate 151 is `Y^64`,
   preparation +X, measurement Z. It has only two batches (128 shots), yet its
   loss doubles broad mean A-risk. The dominant mean variance increment is
   `Y_y` (4.467674 scaled risk units). The four near-nominal, long-coherence,
   detuned, and readout families have this circuit as their worst aggregate
   loss. This suggests lack of redundant sensitivity to the Y rotation angle,
   not merely a loss of many shots. Candidate 562 (`I^32`, +X/Z) shows the
   analogous, smaller vulnerability for `I_y`.

2. **Readout/decoherence confounding.** Candidate 25 is a single Y gate,
   preparation +Y, measurement Y. Its loss raises overall broad risk 1.729774x
   and anisotropic-family risk 2.189471x. A diagnostic counterfactual that fixes
   both readout parameters removes 99.74% of the mean risk increment. The
   dominant affected targets are X, I, and Y depolarization rates. This is a
   calibration-reference dependency: the nuisance treatment amplifies loss of
   this short circuit. The counterfactual is explanatory only and is not used
   for any submitted score.

3. **Sparse decay-rate separation under mixed errors.** Candidate 59 is
   `(XI)^32`, preparation +X, measurement X. It is the worst aggregate loss
   in the broad mixed regime (2.357872x) and produces the largest pointwise
   inflation (21.268719x). The principal mean variance increase is
   `X_depolarization_rate`, followed by I and Y decay rates. Its worst loss
   information eigenvalue across the broad draws is about 0.00240, vastly
   larger than the 1e-10 ridge: this is not an artificial numerical singularity.

The mechanisms are inferred from the exact covariance-increment decomposition,
leverage residuals, and known-readout counterfactual. They identify plausible
robustness objectives for a later generation, but do not establish a target or
prove that a stronger outage-robust design is achievable within this budget.

## Reproduction

From `concept_1/`:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python adversary/portfolio/loss_audit.py --broad-limit-per-family 500
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python adversary/portfolio/loss_audit.py --check-only
```

The second command rechecks the most important loss witnesses at three
finite-difference step sizes and compares direct inversion with the
Sherman-Morrison update. Results are in `loss_numerical_checks.json`.

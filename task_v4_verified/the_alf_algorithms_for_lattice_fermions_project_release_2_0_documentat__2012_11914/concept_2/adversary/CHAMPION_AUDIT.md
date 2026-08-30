# Private generation-1 champion adversary audit

**No participant, target, evaluator, or status edits were made by this audit.**
The final fresh submission is immutable and matches the snapshot hash
`a9be7ed0c86880a6049fa135ca52d51a3ff2b6e3b718662ee6d8ba3701bb57f6`.
All witnesses, fresh source, fixtures, scripts, and numerical records stay
private. This is an audit report, not authorization to build generation 2.

## Strongest usable failure law

Keep the original `flux_disordered` hopping, bond-disorder, dimerization, and
Peierls-phase laws. Replace independent onsite fields by a coherent continuous
frozen-field law:

`V_i = A*s*(1 + rho*eta_i) - mu`, with independent instance draws
`A ~ U[0.5,2]`, `rho ~ U[0.05,0.20]`, `mu ~ U[-0.4,0.4]`, an equiprobable
global sign `s`, and independent site draws `eta_i ~ U[-1,1]`.

These onsite matrices are **nonconstant**. The added ingredient is spatial
correlation, not extreme field strength or stronger flux. It is a new sampling
law over physical frozen one-body field configurations, not a claim that these
samples were drawn independently under the original onsite law or that an
interacting-QMC measure has been simulated. The full machine-readable proposal
is `recommended_physical_law.json`.

### Independently verified modest-step failures

Both entries use repetition count 4 and the original equal-cost 33-stage Strang
reference. The reported errors are relative Frobenius propagator errors.

| Shape | h | Champion error | Strang error | Ratio |
|---|---:|---:|---:|---:|
| 4x4 | 0.4 | 0.004818928579652 | 0.003143844972423 | **1.532813679403** |
| 6x6 | 0.6 | 0.006240217878570 | 0.005188272030795 | **1.202754566748** |

Both failures are confirmed by independent **70-decimal-digit** matrix
calculations and a separate SciPy `expm` implementation. The first failure
already occurs at the old maximum step. The second proves that the failure is
not confined to a circumference-four lattice. At these particular points the
champion still improves the Green-function error: ratios 0.541712 and 0.408065.
This is a robust propagator-tail regression, not a claim that every observable
or overall family score is worse.

### Broad, unselected correlated-field cohorts

Each small/large cohort contains 192 independently drawn configurations,
balanced over `4x4,4x6,6x4` or `6x6,6x8,8x8`, respectively. Counts below are
configurations with a propagator ratio above 1.15 at either tested repetition.

| h | Small failures | Small maximum | Large failures | Large maximum |
|---|---:|---:|---:|---:|
| 0.4 | 1/192 | 1.532814 | 0/192 | 0.941542 |
| 0.6 | 7/192 | 1.845534 | 1/192 | 1.202755 |
| 0.8 | 15/192 | 1.976780 | 3/192 | 1.377622 |
| 1.0 | 21/192 | 2.018285 | 9/192 | 1.476031 |

The small-lattice maximum at h=1 is also checked in high precision. Independent
coherent binary fields with a small defect density and exactly uniform fields
also show regressions; those are supporting experiments, not required parts of
the proposed continuous-field law. Local perturbation experiments are saved
separately and are **not** proposed as a seed-centered hidden distribution.

## Original laws and the geometry hypothesis

- 1,536 original-law cases, 24,576 points: core 2.966586, worst family
  2.597867, maximum point ratio 1.057858; no 1.15-cap failure.
- Another 1,536 independent original-flux-law cases: no failure at h=0.4;
  increasing h to 1 produces six failing configurations, maximum 1.329330.
- 384 larger-torus cases with unchanged original couplings and original steps:
  maximum ratio 0.904235; no regression. A separate 384-case larger-flux cohort
  remains below the cap even through h=1 (maximum 1.075129).
- 576 controlled uniform-real-hopping cases across all six shapes at h=0.4:
  maximum ratio 0.685798; no regression.
- Directly computed uniform-matching commutators are zero along a length-four
  direction and have Frobenius norm divided by sqrt(N) equal to sqrt(2) along
  tested length-six/eight directions. The proposed algebra difference is real,
  but **these controls do not support blaming the observed failure on that
  difference alone**.
- Larger-step ordinary-flux failures, stronger independent fields/phases,
  checkerboard, stripe, block-domain, and uniform-field cohorts are retained
  in `champion_audit_v1/`. Strong independent HS fields alone did not defeat
  the champion in this sweep. No constraint or target was adjusted afterwards.

## Supported root-cause interpretation

For the strongest 4x4 witness at h=0.4, propagator ratios under controlled
changes are:

| Intervention | Ratio |
|---|---:|
| Unchanged | 1.532814 |
| Subtract scalar onsite mean | 1.532814 |
| Set onsite matrix to zero | 1.543141 |
| Set Peierls phases to zero | 0.755597 |
| Make all hopping magnitudes one | 1.620175 |
| Halve hopping magnitudes | 0.918187 |

The evidence supports a finite-step kinetic/Peierls-flux weakness exposed by
weakly varying onsite backgrounds. It is not caused by a large scalar field,
an extreme onsite coupling, an unstable Green-function inverse, or one exact
commuting onsite matrix. This is an empirical interpretation, not a universal
commutator-error theorem. Full step curves, controlled matrices, and ordinary
flux neighborhoods are stored alongside the fixtures.

## Numerical trust and reproduction

The broad oracle diagonalizes H for the exact Fermi function. For each
palindromic positive schedule it forms a half product L such that P=L L*,
obtains P's eigenvectors/eigenvalue logarithms via SVD(L), and evaluates
`G = U diag(expit(-r*log(lambda))) U*`. It never uses an inverse of I+P^r for
scoring. Propagator comparisons share a logarithmic scale; padding is removed
from physical Frobenius denominators. Worst-case checks instead independently
multiply all 33 analytic two-site/onsite exponentials at 70 digits and use
Hermitian eigendecompositions of both H and the completed P.

Direct inversion was explicitly compared as a diagnostic: some h=1 uniform
cases have condition numbers around 6e11 and inverse-versus-spectral Green
disagreement around 1e-5. Those unstable inverses are not the failure oracle.
The highlighted h=0.4 and 0.6 cases have condition numbers only about 282 and
168, respectively. High-precision reports retain both diagnostics.

From the concept root, reproducible private commands are:

```sh
python3 adversary/champion_audit.py
python3 adversary/champion_audit.py --large-only
python3 adversary/cluster_champion_failures.py
python3 adversary/coherent_flux_audit.py
python3 adversary/verify_champion_failure.py --directory adversary/champion_coherent_flux_v1 --regime near_uniform_small --dtau 0.4 --digits 70 --count 1
python3 adversary/verify_champion_failure.py --directory adversary/champion_coherent_flux_v1 --regime near_uniform_large --dtau 0.6 --digits 70 --count 1
python3 adversary/finalize_champion_audit.py
```

`CHAMPION_AUDIT_SUMMARY.json` records counts, artifact hashes and all completed
high-precision checks. `champion_coherent_flux_v1/*_worst_fixtures.json` contains
the strongest private fixtures; the corresponding `_high_precision.json`
files contain independent confirmations.

## Eventual ratchet boundary

Only build after parent authorization. Explicitly publicize any added field
law, shapes and steps, then create **independent new public training draws**
and an independently frozen hidden suite. Do not publish these exact private
fixtures, any previous fresh source/witness, or privileged design artifacts.
Keep the weak runnable Strang baseline public. The prior champion is a private
comparison/control only. Parent owns new targets and generation status.

# Arrays, forward model, population, and objective

All archives are ordinary NPZ, loaded with `allow_pickle=False`. Energy is meV,
temperature is K, and `k_B = 0.08617333262 meV/K`. Arrays are float64 unless noted.
The row ordering has no physical meaning. No case IDs or family codes are given
at inference. Training and validation have the same input contract as inference.

## Input and labels

| Input key | Shape | Meaning |
|---|---|---|
| `omega_mev` | `[192]` | Positive midpoint grid, `0.3125 + 0.625*j` |
| `domega_mev` | `[192]` | Quadrature weights, all `0.625` |
| `matsubara_index` | `[40]`, int64 | Nonnegative integer bosonic indices |
| `temperature_k` | `[B]` | Measurement temperature, independent of spectrum |
| `nu_mev` | `[B,40]` | `2*pi*k_B*temperature_k*matsubara_index` |
| `interaction` | `[B,40]` | Noisy dimensionless interaction; masked entries zero |
| `mask` | `[B,40]`, bool | True for an observed entry; index zero always observed |
| `noise_std` | `[B,40]` | Known marginal standard deviations, including masked entries |
| `noise_rho` | `[B]` | Correlated fraction |
| `noise_length` | `[B]` | Correlation length in observation-slot index units |
| `mu_star` | `[B]` | Specified Coulomb pseudopotential for the Tc diagnostic |

Public files: `train_input.npz`, `train_labels.npz`, `validation_input.npz`,
`validation_labels.npz`. Labels contain `alpha2f[B,192]` and `family[B]` (int64).
No clean interactions, generator parameters or random seeds are public.
The hidden batch has 384 independent rows, 96 per family, shuffled together.
`B` must not be hardcoded. The output archive has **exactly one key**, `alpha2f`;
its dtype must be real numeric, finite, nonnegative, and shape `[B,192]`.
Each row must have positive integrated coupling. No separate property predictions.

## Exact discrete forward and noise model

Let `a_j = alpha2f[j]`. In the stated energy convention `a_j` is dimensionless.
The benchmark's exact forward model is midpoint quadrature:

```
lambda_j = 2 * domega_j * a_j / omega_j
Lambda(nu) = sum_j lambda_j * omega_j**2 / (omega_j**2 + nu**2)
interaction_r = Lambda(nu_r) + epsilon_r
C_rs = noise_std_r * noise_std_s * (
    (1-rho) * delta_rs + rho * exp(-abs(r-s)/noise_length))
epsilon ~ Normal(0, C)
```

Here `r,s` are slots 0..39, NOT Matsubara indices or frequencies. For masked
observations use the appropriate principal covariance submatrix; missing slots
are not measurements of zero. Every case has 30..40 observations. Noise scale,
mask, measurement temperature and `mu_star` are drawn independently of spectral
parameters and family, so metadata are not disguised spectral labels. The
spectra do not change with measurement temperature. Temperatures are 1.8..6 K,
`rho` is 0.30..0.85, noise length is 1.5..5.5 slots, and the independent noise
scale is 0.0003..0.0020. Marginal standard deviations decrease smoothly toward
large `nu` and are explicitly provided. No unknown systematic offset is added.

## Disclosed population

All spectra are synthetic, positive sums of smooth acoustic and optical bands,
with a quadratic low-energy onset and a smooth upper cutoff at 120 meV. They are
physically admissible phenomenological spectra, **not EPW/DFPT material data**.
Total coupling is 0.55..2.4, and `mu_star` is 0.09..0.16. Peak locations, widths,
weights and gentle band asymmetries vary continuously. Optical widths start at
about 1.2 meV; there are no delta functions, signed spectra, or arbitrary labels.

| Code | Family | Broad variation |
|---|---|---|
| 0 | acoustic_dominated | Strong broad acoustic contribution, weaker separated optical bands |
| 1 | soft_optical | Substantial optical weight at roughly 3.5..11 meV, plus acoustic and higher modes |
| 2 | split_optical | Overlapping/split middle-energy optical bands and a weaker remote band |
| 3 | broad_multiband | Several broad asymmetric optical bands over a variable acoustic background |

Every family is equally represented in training, validation and test. Test uses
new continuous parameters and noise, not undisclosed categories or out-of-range
distributions. Exact latent mixture recipes are intentionally private. Finite
noisy Matsubara data do not uniquely identify every fine peak: performance is
assessed statistically using transport distances, not exact pointwise recovery.

## Score (fixed version 1.0)

For each spectrum let `lambda = sum(lambda_j)` and `p_j = lambda_j/lambda`.
The two spectral errors are exact one-dimensional Wasserstein-1 distances
between the discrete coupling distributions, on `log(omega/meV)` and on `omega`:

```
Wlog = sum_j<191 abs(cumsum(p_pred-p_true)[j]) * log(omega[j+1]/omega[j])
Wmev = sum_j<191 abs(cumsum(p_pred-p_true)[j]) * (omega[j+1]-omega[j])
wlog = exp(sum_j p_j * log(omega_j/meV)) * meV
Tc = wlog/(1.2*k_B) * exp(-1.04*(1+lambda)/(lambda-mu_star*(1+0.62*lambda)))
```

Set `Tc=0` if the exponent denominator is nonpositive. This is the simplified
McMillan–Allen–Dynes diagnostic used in Eq. (16) of the EPW paper, **not a full
Eliashberg gap-equation solution or the strong-coupling-corrected expression**.
Also report `sqrt(sum(p_j*omega_j**2))` as an unscored second-moment diagnostic.
We do not infer resistivity or `alpha2F_tr`: that would require information about
momentum relaxation not present in these isotropic interaction measurements.

```
case_loss = 0.55 * Wlog/0.10 + 0.10 * Wmev/3.0
          + 0.10 * abs(log(lambda_pred/lambda_true))/0.035
          + 0.10 * abs(log(wlog_pred/wlog_true))/0.06
          + 0.15 * abs(log((Tc_pred+2 K)/(Tc_true+2 K)))/0.08
score = 100 * exp(-mean(case_loss))
```

Core score averages all rows; each family score uses only that family's rows;
worst-family score is the minimum. **Pass requires core ≥80 and worst-family
≥70**, valid output and resource compliance. Errors cannot cancel and no
individual dimension is clipped. Invalid output or solver failure scores zero.
The 2 K stabilizer avoids amplifying arbitrarily small Tc. Wlog resolves the
importance of soft phonons while Wmev also penalizes misplaced high-energy weight.
Forward whitened residuals are reported diagnostically, not rewarded as a proxy
for recovering the spectrum. A noise-interpolating spike train is not a solution.

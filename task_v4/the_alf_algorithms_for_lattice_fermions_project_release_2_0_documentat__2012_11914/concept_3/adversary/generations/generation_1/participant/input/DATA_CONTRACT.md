# Data and objectives

## Assets and independence
`train_input.npz` and `train_labels.npz` provide 1,536 independent cases,
256 per family. `validation_input.npz` and `validation_labels.npz` provide
192 independent cases, 32 per family. Hidden evaluation has 192 cases,
32 per family, generated independently from the same population. Spectra,
observation noise, shuffles and random identifiers use separate random streams.
No latent spectrum is intentionally repeated across splits. No test-only
families or secret distribution shifts exist. Public labels may be used for
training. Seeds, hidden labels and hidden family assignments are private.
Identifiers and file ordering have no physical information.

## Input arrays
NPZ files are loaded with `allow_pickle=False`. All floating inputs are float64.
Let N denote batch size, T=56 and M=256.

| Key | Shape | Definition |
| --- | --- | --- |
| sample_id | (N,), uint64 | Opaque unique IDs, preserve order |
| omega_edges | (257,) | Uniform energy-bin edges from -8 to 8 |
| beta | (N,) | Inverse temperatures uniform on [6,28] |
| tau | (N,56) | Increasing imaginary times, including 0 and beta |
| correlation | (N,56) | Noisy positive-sign fermionic correlations |
| covariance | (N,56,56) | Full SPD covariance of each supplied observation |

Labels contain `sample_id`, `spectral_mass` (N,256), integer `family_id` (N,),
`low_mass` (N,), `band_weights` (N,5), and `gap10` (N,). The last three are
derived from the spectral masses, not independently assigned properties.

## Forward problem
`spectral_mass[j]` is probability in a bin, NOT spectral density at its center.
The density is constant within each bin, equal to mass divided by bin width.
For the positive-sign convention used here,

```
C(tau) = integral A(omega)*exp(-tau*omega)/(1+exp(-beta*omega)) d omega
C = K @ spectral_mass
```

Thus C=-G under the common negative Green-function convention. Do not negate
the provided correlations. Six-point Gauss-Legendre quadrature computes the
bin-average kernel; `physics.kernel` is the exact numerical definition used
to generate observations. There is no hidden quadrature mismatch, extra
broadening or unreported moment constraint. The log-add-exp form is stable.

Time fractions start at 56 cosine-spaced nodes in [0,1], with interior jitter
uniform within 15% of the smaller neighboring separation, then multiply by
beta. Noise is zero-mean multivariate Gaussian with the exact supplied
covariance; it is not an estimate needing a sample-count correction. Base
amplitude is log-uniform on [3e-5,1.2e-3]. Covariance combines a diagonal part
and an exponential time-fraction correlation with length uniform on [0.03,0.18]
and mixing weight on [0.2,0.85]. It adds a rank-one cosine component of weight
[0,0.25] and phase [-0.5,0.5]. Per-time amplitude is multiplied by
`0.65+0.35*cos(2*pi*tau/beta)**2`. Noise, covariance, beta and time-grid jitter
are independent of both spectrum and family; covariance does not encode labels.

## Physical population
These are positive, normalized synthetic spectral models inspired by physical
phenomenology, not exact solutions of six microscopic Hamiltonians or actual
ALF Monte Carlo runs. All uniform intervals below are continuous and independent
unless constrained. Energies are in supplied units. Profiles are sampled at bin
centers then normalized over [-8,8]; Gaussian tails outside support are discarded.
Gaussian width means standard deviation. A continuum has profile
`max(1-z*z,0)**shape * exp(skew*z)` inside |z|<1, with
`z=(omega-center)/half_width`. Components are individually normalized before
positive weighted mixing. The minimum peak width is 0.09, not a delta function.

- Family 0, coherent quasiparticle: Gaussian center [-0.4,0.4], width
  [0.09,0.24], weight [0.4,0.85]; background continuum center [-0.8,0.8],
  half-width [2,4], skew [-1.2,1.2], shape [0.3,1.8].
- Family 1, Hubbard metal: Gaussian bands separated by [1.6,4.6], common
  center shift [-0.65,0.65], independent widths [0.4,1], left-band fraction
  [0.25,0.75]. A central Gaussian has weight [0.10,0.45], center [-0.25,0.25],
  width [0.09,0.26]; the band weights share the remaining mass.
- Family 2, Mott insulator: same two-band ranges, no central Gaussian. Multiply
  each band by `clip((abs(omega)-gap)/ramp,0,1)` then renormalize. Gap is
  uniform on [0.25,min(1.3,separation/2-0.1)]; common ramp width [0.10,0.35].
- Family 3, pseudogap: continuum center [-0.6,0.6], half-width [2,4.5], skew
  [-1.4,1.4], shape [0.2,1.6]. Multiply by a Gaussian notch
  `1-depth*exp(-0.5*((omega-notch_center)/notch_width)**2)` with center
  [-0.12,0.12], width [0.25,1], depth [0.60,0.98]. Add a similarly notched,
  individually normalized Gaussian shoulder with weight [0,0.25], center of
  equally probable sign and magnitude [0.6,1.5], width [0.2,0.5].
- Family 4, asymmetric continuum: continuum center [-1.2,1.2], half-width
  [2.2,4.8], skew [-2,2], shape [0.2,1.8]. Gaussian satellite with equally
  probable center sign, center magnitude [1.5,4.8], width [0.25,0.9], weight
  [0.08,0.4].
- Family 5, multiband continuum: uniformly choose 3, 4 or 5 continuum bands,
  centers [-4.8,4.8], half-widths [0.45,1.5], skews [-1.5,1.5], shapes
  [0.2,1.6], weights from symmetric Dirichlet concentration 2.

## Output and validity
Write exactly three arrays: `sample_id` unchanged uint64, `spectral_mass`
(N,256), and `low_mass_quantiles` (N,3). Numeric predictions must have a real
floating dtype, finite values in [0,1]. Mass rows sum to one within absolute
tolerance 1e-6, with tiny normalization deviations corrected before scoring.
Zero mass bins are allowed. Quantiles are nondecreasing 10%, 50%, 90% predictions
for the latent mass in [-0.5,0.5], NOT future measurement noise. They need not
be centered on the spectral point estimate. Extra arrays (including purported
timings), object arrays, wrong shapes, reordered IDs, nonfinite values,
negative mass or invalid normalization fail. Compressed and expanded prediction
NPZ sizes must each be at most 16 MiB.

## Spectral functionals and scores
`physics.py` and `scoring.py` are the executable definitions. W1 exactly
integrates the absolute difference of piecewise-linear spectral CDFs, including
within-bin zero crossings, and is normalized by support length 16. Low-energy
mass integrates [-0.5,0.5]. Five band weights partition edges
[-8,-2,-0.5,0.5,2,8]; their error is half the L1 difference.
`gap10` is the smallest radius containing 10% of mass in [-radius,radius],
interpolated within shells. This is a robust depletion scale, NOT the exact
hard-gap location, which would be unstable to infinitesimal spectral tails.

Per case, w is normalized W1, l is absolute low-mass error, b is band error,
g is absolute gap10 error. q is mean pinball loss across alpha=0.1,0.5,0.9,
with `pinball=max(alpha*residual,(alpha-1)*residual)` and
`residual=true_low_mass-predicted_quantile`.

```
loss = 0.45*w/0.02 + 0.20*l/0.06 + 0.15*b/0.10
     + 0.10*g/0.40 + 0.10*q/0.02
core_score = 100*exp(-mean(loss))
family_score = 100*exp(-mean(loss within family))
worst_family_score = min(family_score)
```

Pass requires core >=90 and worst family >=85, valid predictions and resource
compliance. Proper quantile loss discourages both unjustified narrow intervals
and uselessly wide intervals. Empirical 80% coverage and interval width are
diagnostics, not additional gates; an exact-label oracle can score 100.
Fine-scale pointwise spectral error is deliberately not the target of this
ill-conditioned inverse problem. No passing solution is guaranteed.

## Invocation and resources
`python3 solve.py INPUT_NPZ OUTPUT_NPZ` receives absolute paths. A single call
handles the batch. Only Python standard library, NumPy and SciPy are promised.
Public input assets are mounted read-only at `/public/input`; submission at
`/submission`; input at `/input.npz`; output under `/output`; scratch at `/tmp`.
`PYTHONPATH=/public/input` exposes the public definitions. Hidden labels,
private code, host home, GPUs and network are inaccessible. Submissions may
package learned assets or load public training labels at runtime. Submission
limit is 100,000,000 bytes and 10,000 regular files; symlinks and special files
are rejected. One CPU core, 120 seconds wall time, 2 GiB per-process address
space and 16 MiB per file are enforced. Model loading and interpreter startup
count; evaluator copying and hashing do not. Runtime comes from the evaluator's
monotonic clock, never a submitted field. `resource_score=100*max(0,1-runtime/120)`
is diagnostic and not blended into scientific accuracy. Bubblewrap failure
fails closed: no host execution fallback exists. External training is allowed.

For a local smoke test, run the baseline on `validation_input.npz`, then use
`check_validation.py PREDICTIONS_NPZ`. This scores only public validation data.

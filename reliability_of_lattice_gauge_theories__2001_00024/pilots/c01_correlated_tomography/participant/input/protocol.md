# Numerical contract, version 1

All inputs and outputs are JSON. Python, NumPy, and SciPy are available. Work
offline. Each call is independent; no case identifier or external lookup is
needed. The input is the complete mathematical definition of the case.

## 1. Oscillatory readout

`tracks` contains distinct named records with equal-length arrays `time_ms`,
`signal`, and strictly positive `sigma`. Negative measured signals are possible;
do not truncate observations. `query_time_ms` contains prediction times but no
observations. A track's calibration supplies `period_ms`, `decay_ms`, and
`phase_rad`. Define

    h(t) = [1 - exp(-t / decay_ms) cos(2 pi t / period_ms + phase_rad)] / 2
    mu(t) = offset + amplitude * h(t).

Return the unique unconstrained minimizer of
`sum_i ((signal_i - mu(time_ms_i))/sigma_i)^2`. Neither coefficient is clipped.
The reported sigmas are absolute weights, not standard errors to be divided by
an unknown shot count. `amplitude_se` is the square root of the amplitude entry
of `(X^T W X)^(-1)`, where `X` has columns `[1,h]` and
`W=diag(1/sigma_i^2)`. Do not rescale this covariance by the residual variance.
Return `prediction=mu(query_time_ms)` in the supplied order.

The period 7.2 ms and decay 96 ms reflect calibrated single-particle tunneling.
The free additive offset, fixed zero phase, and covariance convention are
explicit pilot readout assumptions, not a claim to reproduce unavailable
detector calibrations. The amplitude is a dimensionless, undamped peak-to-peak
population response, not the coefficient of a unit sine.

## 2. Correlated occupation certificate

`occupation.states` lists the allowed triples `(left gauge, matter, right gauge)`
in the order used by every response vector and witness. The latent vector `p`
is any nonnegative distribution over these states with `sum(p)=1`. States not
listed have exactly zero probability **as a conditional model assumption**.
Do not assume reflection symmetry, independent occupations, or a unique `p`.

Every `observation` has a numeric `response` vector, an `id`, and one of two
ways to define its measured center `v` and radius `r > 0`:

- A density record directly supplies `center` and `radius`.
- A fitted record supplies `amplitude_weights`, `sigma_multiplier`, and
  `systematic_radius`. Its center is `sum_track weight * amplitude`; its radius
  is `sigma_multiplier * sqrt(sum_track (weight * amplitude_se)^2) +
  systematic_radius`. Omitted weights are zero. The track fits in section 1
  determine these quantities; they are not adjustable in the occupation step.

The independently fitted tracks are treated as uncorrelated only for this
declared radius construction. All bands are simultaneous deterministic error
envelopes, **not** a coverage-calibrated statistical confidence region.

First determine the smallest `inflation >= 0` for which a distribution exists
satisfying, for every observation,

    abs(dot(response, p) - v) <= r * (1 + inflation).

Next define the feasible set using `inflation_star + feasibility_pad`, where
`feasibility_pad` is supplied in the input (dimensionless). For each target in
`occupation.targets`, return the minimum and maximum of
`dot(target.coefficients,p)` over that same feasible set, and a feasible
distribution attaining each endpoint. Distinct endpoints may have distinct
witnesses. A positive inflation diagnoses incompatible original envelopes; do
not silently discard constraints. Endpoints are conditional identified-set
bounds, never inferred true state populations.

The gauge-invariant configurations are `010`, `002`, and `200`. The target
`gauge_valid` is their total probability; the local violation interval is
therefore `[1 - gauge_valid_upper, 1 - gauge_valid_lower]`. Individual target
intervals cannot in general be added to obtain the sharp total interval.

Responses are provided numerically, so no apparatus trivia is required. Their
physical meaning is: `matter_mean` is the central occupation; `link_doublon`
is the average of the two link indicators for occupation 2; `A` and `B` detect
central occupation 1 with the respective neighboring link empty. The sum of
the two split-doublon signals depends on both links and can include contaminant
occupations. Use the supplied response, not a guessed single-state indicator.

Cases vary occupation support and available correlated channels. A missing
observation is intentionally unconstrained, even when its track is present for
readout scoring. The `family` and `case_id` fields are descriptive only.

## Output

    {
      "fits": {
        "<track id>": {"offset": number, "amplitude": number,
                       "amplitude_se": number, "prediction": [number, ...]}
      },
      "inflation": number,
      "bounds": {"<target id>": [lower, upper]},
      "witnesses": {
        "<target id>": {"lower": [probability, ...],
                        "upper": [probability, ...]}
      }
    }

Return all supplied tracks and targets; all numbers must be finite. Witness
lengths must equal the number of allowed states. There is no prose score.
Fit errors, bound errors, inflation errors, witness feasibility, and endpoint
attainment all matter. Accuracy around `1e-7` is sufficient for numerical
certificates. Wall-time limit: 120 seconds per case, including isolation startup,
with a 6 GiB memory budget. Numerical reference work normally takes under a second.

Each bottleneck uses a continuous score `1/(1 + loss/weak_loss_scale)`, relative
to a fixed, private weak baseline, with a small positive scale floor. Thus a
matching reference scores 1 and the baseline ordinarily scores 0.5; there is
no broad correct-answer tolerance plateau. The case core is the geometric mean
of the two bottleneck scores. Reports include equally weighted family means,
their macro-average, and the worst family. Only one unlabeled example is public.

# Compact NLO response with endpoint power corrections

Deploy a color-resolved NLO EEC response that preserves next-to-leading-power
information, not only the much larger leading-power spectrum. The supplied
champion fits the density accurately but loses accuracy when extracting these
endpoint remainders. Improve it within its existing 268-scalar footprint.

For `t=log(z/(1-z))`, the physical density is `F=z(1-z)B_channel`. The scored
response H equals `(F-F_LP)/(z(1-z))` for `t<-4` and `t>=4`, using the appropriate
collinear/back-to-back leading-power term; H equals F centrally.
`input/endpoint_terms.json` and `workspace/model.py` define the terms and exact
deployment semantics. `input/calibration.npz` provides accurate H, dH/dt and F
samples. The source-native calculation is unavailable.

Write a static `model.json` with common increasing `knots` spanning exactly
[-24,24], three Chebyshev coefficient lists per interval in `coefficients`, and
optional interval `charts`: `density`, `collinear`, or `backward`. The last two
store the respective remainder and are confined to `t<=-4` and `t>=4`.
Missing charts mean density, as in the champion. At most 268 scalar entries
(knots plus coefficients), 20 intervals and degree 64 per list are allowed.
Charts are discrete metadata, not additional coefficients.

Hidden tests require mixed error at most `2e-8*(1+abs(truth))` for H, signed
channel combinations with L1 norm at most one, and physical finite-bin F
averages; dH/dt has tolerance `2e-7*(1+abs(truth))`. One-sided knot behavior is
included. Meet every tolerance and reduce the champion's maximum tolerance
ratio at least 100-fold. Aggregate accuracy, worst-family accuracy and bounded
deployment size are reported. Submitted code is never executed.

`python workspace/check.py /path/to/output` checks calibration accuracy.
`python baseline/build.py /path/to/output` copies the runnable champion baseline.
NumPy, SciPy and mpmath are available for construction. The budget is one hour.

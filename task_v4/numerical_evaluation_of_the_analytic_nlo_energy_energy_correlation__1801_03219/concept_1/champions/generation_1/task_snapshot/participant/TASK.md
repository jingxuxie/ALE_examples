# Compact color-resolved EEC response

Deliver a deployable compressed response for precision fits of the analytic
NLO energy-energy correlation. The three channels in `input/calibration.npz`
are the leading-color, subleading-color and flavor coefficients, with
`t = log(z/(1-z))` and `F(t) = z(1-z) B_channel(z)`. Thus an integral of F
over t is the corresponding finite-angular-bin integral of B over z.

The calibration table gives F and dF/dt over `-24 <= t <= 24`. The runnable
baseline and `workspace/model.py` define the deployment format and its exact
semantics. The native calculation is unavailable.

Write `model.json` into the requested output directory. It contains shared
increasing `knots` spanning exactly [-24,24] and, for each interval, three
Chebyshev coefficient lists in `coefficients`. At most 320 scalar entries
(all knots plus all coefficients), 20 intervals, and degree 64 per list are
allowed. Values must be finite real JSON numbers. No executable is submitted.

Hidden tests cover channel values, angular derivatives, finite-bin averages,
and signed channel combinations with coefficient L1 norm at most one throughout
this domain. Required mixed errors
are `2e-8 * (1 + abs(truth))` for values and bin averages, and `2e-7 *
(1 + abs(truth))` for derivatives, including one-sided knot behavior. The target
is to meet every tolerance within the deployment budget, improving the supplied
baseline by at least two orders of magnitude in its maximum tolerance ratio.
Scoring reports aggregate accuracy, the worst test family, and deployment size.

`python workspace/check.py /path/to/output` checks public calibration accuracy.
Python, NumPy and SciPy are available for artifact generation. The construction
budget is one hour; grading only interprets the bounded JSON artifact.

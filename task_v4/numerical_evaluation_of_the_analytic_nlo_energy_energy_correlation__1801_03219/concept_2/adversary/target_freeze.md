# Target frozen before privileged search

2026-08-28. No fresh agents are launched here.

The target is real binary64 embedded Gauss(10)/Kronrod(21) quadrature,
with four pilot panels, compulsory bisection to eight panels, QUADPACK-style
absolute-deviation error rescaling, a 50-epsilon absolute-integral floor,
parent/children discrepancy guards, largest-local-error bisection, and a
512-leaf cap. Absolute tolerance is 2e-8 and relative tolerance is 2e-9.
Error estimates are summed as nonnegative local quantities, never signed.

The finite weight domain has 12 consecutive Fourier frequencies, at most 64,
24 lattice coefficients at spacing 1e-10, coefficient l1 <= 1 and Fourier
RMS >= 0.1. The quadratic positive detector response has two small discrete
parameters. Three finite bins are available; neither endpoint is approached
closer than 0.02. The same weight must defeat each of the three actual QCD
color contributions (Nc=3, Nf=5), not arbitrary unphysical color factors.

For every family, require target success and conservative true quadrature
error >= max(20*tolerance, 50*estimated_error, 1e-5*reference_L1).
Reference agreement and frozen/source kernel agreement are separate gates.
No value-at-bin-center shortcut, discontinuity, tunable feature width, direct
node-factor polynomial, injected numerical bug, or low-accuracy source kernel
is permitted. Fourier weights can be signed because they are linear moments,
not event probability densities. Passing all three families is full success.

This is a white-box inverse numerical-design problem. A structured search
using the known error functionals is allowed. Blind random failures alone
will not be represented as proof of hardness.

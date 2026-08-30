# Public distribution and uncertainty

Define `s=(lambda/6)^(1/3)`, `r=mu2/s^2`, `j=kappa/s^2`. Before numerical
admission, independent draws use:

| Quantity | Distribution |
| --- | --- |
| L | Balanced between 2 and 3 |
| regime | Balanced single / crossover / double |
| r, single | Uniform [0.35, 3.5] |
| r, crossover | Uniform [-1.4, 0.35] |
| r, double | Uniform [-4.2, -1.4] |
| j | Uniform [0.12, 1.0] |
| s | Log-uniform [0.6, 1.6] |
| omega_0/s | Log-uniform [0.30, 2.4] |

Each case exposes both `omega_0` and `1.4*omega_0` at cutoffs 4, 6, 8. Regime
names are sampling bins, not claims of a thermodynamic transition; negative r
also occurs in the crossover bin. Basis frequency changes approximation error,
not the underlying physical Hamiltonian. All six families occur in every split,
with 32 training, 8 validation, and 12 hidden cases per family. Physical draws
are independent between splits, not paired rescalings or shared realizations.
This is extrapolation in local Hilbert cutoff on unseen Hamiltonians, not
out-of-support extrapolation in all Hamiltonian parameters.

Admission conditions, applied identically to all splits: every dimensionless
gap is at least 1e-6; the last two consecutive cutoff increases each change
every gap by at most 2e-5 in absolute log ratio; an independently chosen
oscillator frequency agrees within 2e-5; residual-plus-roundoff/gap is at most
2e-6; each final state residual is at most 1e-10 dimensionless. Rejected draws
are replaced within their family, so the released distribution is conditional
on these criteria. Sampling is never conditioned on predictor performance.

Labels are the last directly computed, high-cutoff reference-basis Ritz gaps.
No fitted or asymptotically extrapolated values are called truth. Convergence
checks and residuals are empirical numerical certificates, not rigorous bounds
on the infinite-cutoff spectral tail. Residuals certify finite-matrix states;
they alone do not certify continuum or infinite-Hilbert-space accuracy. The
declared gap floor avoids subtraction at machine-resolution scales. Full
certificates, generator realization and hidden targets stay with the evaluator.

# Contract

All times and energies are dimensionless, hbar=1. `case` contains `calibration`
(a list of small-chain experiments), `experiment` (the prediction settings),
`times`, and `pairs`. Settings define `length`, `spin`, `J`, `mass`, `electric`,
`V`, `protection` (`full` or `linear`), `coefficients`, and `profile`.

There are L cells, each with a two-level matter site and its right link. Local
basis order is `(n,m)` with n=0,1 and m=-S,-S+1,...,S; the matter index is outer.
`profile[j]` is a known mass detuning. The left boundary flux is fixed at -S.
The rightmost link is dynamical; there is no hop beyond the chain. Initially
n_j=0 and m_j=(-1)^j S, with j=0,...,L-1. Define n=(sigma_z+1)/2 and the usual
spin-S ladder matrix elements. The model is

    H = sum_j [(mass + profile[j] + delta_mass) n_j
               + electric/2 (s_z,j)^2
               + lambda_link (s_plus,j+s_minus,j)/sqrt(S(S+1))]
        + sum_{j=0}^{L-2} [ -J/sqrt(S(S+1))
              (sigma_minus,j s_plus,j sigma_minus,j+1 + h.c.)
              + lambda_pair (sigma_minus,j sigma_minus,j+1 + h.c.) ]
        + V H_pro.

    G_j = (-1)^j [s_z,j-1 + s_z,j + n_j], with s_z,-1=-S.
    H_pro = sum_j G_j^2                    (full)
          = sum_j coefficients[j] G_j     (linear).

Three unknown, device-wide real parameters are shared by calibration and
prediction: `parameters = [lambda_pair, lambda_link, delta_mass]`, with
0.025 <= lambda_pair,lambda_link <= 0.30 and -0.25 <= delta_mass <= 0.25.
Calibration records contain their own `settings`, `times`, `pairs`, and observed
`density`, `violation`, `correlation`; entries have independent Gaussian noise
with standard deviation `noise_sigma` (normally 2e-6). Known parameters are exact.

Return a dictionary with `parameters` and these arrays at every requested time:

- `density[t][j]` = <n_j>.
- `violation[t][j]` = <G_j^2>, even when protection is linear.
- `correlation[t][p]` = <n_left n_right> - <n_left><n_right> for `pairs[p]`.

Shapes are exactly (number of times, L), (number of times, L), and
(number of times, number of pairs). Do not time-average any output. Correlations
are signed. All values must be finite. Times start at zero and increase.
Hidden lengths range from 24 to 64, S is 1/2 or 1, V ranges from 0 to 12, and
times extend to 10. Inhomogeneous profiles and full/linear protection both occur.
The per-case evaluation budget is 3600 wall seconds on one CPU and 6 GiB.
This is distinct from the runner's one-hour development limit.

Each numerical block is independently scored against a converged reference with
a continuous error-based score, normalized by a factorized weak predictor's error.
Component scores combine geometrically so one failed technical component cannot
be averaged away. There is no accuracy plateau. Reference numerical uncertainty is audited before
evaluation. Aggregate reporting includes component scores and worst physical
family; a correct fit alone cannot solve the dynamics.

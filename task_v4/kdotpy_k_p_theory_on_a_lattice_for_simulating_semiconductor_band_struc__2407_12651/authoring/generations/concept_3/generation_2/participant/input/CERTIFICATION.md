# Generation 2: four-band continuum and topology certificate

All four eigenstates of the fixed model in SPEC.md are retained. The evaluator
independently assembles 4-by-4 Fourier matrices T_R, rather than importing public
helpers. It uses a periodic 320-by-320 momentum mesh and five equally spaced
samples including endpoints in each of u and v. Private audits add no restrictions.

Let Lx=sum |Rx| ||T_R||+0.06 and Qx=sum Rx^2 ||T_R||+0.06, and similarly Ly,Qy.
For coordinates (kx,ky,u,v), set L=(Lx,Ly,1,sqrt(2)), Q=(Qx,Qy,0,0), and
h=(2*pi/320,2*pi/320,0.10/4,0.12/4). All norms are operator norms.

The preliminary uniform gaps are
`a=min_grid(E1-E0)-sum L_j h_j` and
`b=min_grid(E2-E1)-sum L_j h_j`.
It is NOT sufficient to use a for both eigenvalue Hessians in four bands.
For the central u,v box the separate bounds are
`M0_j=Q_j+2 L_j^2/a` and `M1_j=Q_j+2 L_j^2/min(a,b)`.
Define `epsilon_n=sum M_nj h_j^2/8`, for n=0,1. These follow from the complete
eigenvector perturbation sum; all denominators for E1 are bounded by min(a,b).
No Hessian of E2 is required.

For independent relative coefficient errors, the uniform perturbation norm is
`eta=0.004 [sqrt(2) sum|spin_orbit| + sum w_pq (|orbital_mass|+|scalar|)]`,
where w=1 if p=q and w=2 otherwise. This is unchanged: embedding a Hermitian
active perturbation in a 4-by-4 zero extension preserves its operator norm.
Require a>0 and b-2*eta>0. The latter separately certifies gap12 across the full
manufacturing box, using a first-order bound rather than an E2 Hessian.

For each sampled u,v compute W_grid, g_direct_grid and g_indirect_grid. Report
`W_cert=max W_grid+2(epsilon0+eta)` and
`g_cert=min g_grid-(epsilon0+epsilon1+2*eta)` for both direct and indirect gaps.
The same uncertainty-interpolation weights apply to each momentum, so these
bounds control each device's bandwidth, not a pooled linewidth across devices.
The entire coefficient box is covered by eta, not by random corner tests.

Topology is independently anchored to the uncoupled two-band core. Its FHS
invariant and spherical degree must agree, and a Fourier Lipschitz cell bound
certifies a nonvanishing continuum homotopy to the core's triangulated vector.
Both fixed remote levels must remain above the core upper band throughout the
Brillouin zone; the evaluator certifies `5.5-max E1_core` by a grid fill bound.

Then H(lambda) interpolates linearly from V=0 to the fixed V, with nine samples
in lambda and a separate 128-by-128 periodic momentum mesh. Let Lx*,Ly* be the
larger endpoint Fourier derivative bounds and B=sum ||T_R(full)-T_R(core+remote)||.
The entire coupling homotopy has gap01 at least
`min_grid,lambda gap01 - 2[(Lx*+Ly*)*pi/128+B/16]`.
It must be positive. The full four-band rank-one FHS invariant must agree with
this independently certified core invariant. A shifted grid and randomized
phases audit FHS. Finally the certified full-model manufacturing gap connects
every allowed manufactured Hamiltonian to the nominal one without closing gap01.

The implementation inflates norms by 1e-12 plus 1e-14 and uses energy padding
2e-10*(1+sum ||T_R||). Homotopy bounds add 1e-9. Topology integer residuals must
be below 2e-8, link magnitudes above 1e-8, and plaquette phases below pi/2.
These are analytic continuum bounds with float64 safety margins, not formal
interval-arithmetic proofs. Reports expose the separate gap01/gap12 and Hessian
bounds. Conservative certificate failure is not proof of physical infeasibility.

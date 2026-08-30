# Exact reduced model

Sites are a rectangular grid, indexed `[row_y, column_x]`, with spacing `h`.
The boolean mask selects superconducting/material sites. A missing site is a
vacuum hole or exterior, not a site clamped to zero with links still attached.
Only horizontal/vertical links with **both** endpoints active contribute. Omitted
links give the discrete natural, covariant zero-normal-current boundary condition.
There are no periodic boundaries or fixed boundary values.

For an oriented link from site `i` to its right/up neighbor `j`, let
`U_ij = exp(-1j * a_ij)`. The exact dimensionless energy is

```
F(psi) = h**2 * sum_active(alpha_i * |psi_i|**2
                         + beta_i/2 * |psi_i|**4)
         + sum_active_links k_ij * |U_ij * psi_j - psi_i|**2.
```

Each undirected link appears once. There is no extra factor 1/2 in the link
term and no division by site count. `beta > 0`, `k > 0`. Negative `alpha` favors
condensation; positive pinning patches suppress it. Geometry and all coefficients
are explicit data, not reconstructed from a private generator. Some cases include
flux through holes as well as bulk magnetic frustration. `ax` and `ay` are link
integrals in radians, not magnetic-field samples. The directed plaquette sum
`ax[y,x] + ay[y,x+1] - ax[y+1,x] - ay[y,x]` is its flux phase.

For any site phase `chi`, transform `psi_i -> exp(1j*chi_i)*psi_i` and
`a_ij -> a_ij + chi_j - chi_i`. Every link difference transforms by the phase at
its source, so the energy is gauge invariant and its complex gradient is gauge
covariant. A global phase is unconstrained. Local gauge changes of the field
alone are not symmetries with fixed input links.

The API gradient `g = dF/dRe(psi) + 1j*dF/dIm(psi)` satisfies
`dF = Re(sum(conj(g_i) * dpsi_i))`. Onsite contributions are
`2*h**2*(alpha + beta*|psi|**2)*psi`. For `d = U*psi_j - psi_i`, a link adds
`-2*k*d` at `i` and `2*k*conj(U)*d` at `j`. Inactive gradients are zero.
Packed vectors concatenate all active real parts then all active imaginary parts,
both in NumPy row-major mask order. Gradient RMS uses these `2*N` real coordinates.

The normal state has energy zero but is generally unstable. When `alpha=-1`,
`beta=1`, `a=0`, a constant unit-modulus field on every active connected component
has energy `-h**2*N/2`, zero gradient, and attains the termwise lower bound.
More generally `-h**2*sum(min(alpha,0)**2/(2*beta))` is a rigorous but usually
loose lower bound. It is **not** the private witness energy.

Physically, GL is a near-critical-temperature (near-`Tc`) approximation. We use
its single-component, static, fixed-vector-potential limit on the supplied finite
grid. Link phases are line integrals of a physical prescribed vector potential:
a smooth applied perpendicular field, optional flux tubes entirely inside vacuum
holes, and a pure gauge gradient. They are not independent random bond frustrations.
All stiffnesses are strictly positive. There is no magnetic self-energy,
self-consistent screening, quasiparticle
spectrum, temperature sweep, continuum extrapolation, or Eilenberger solver.
Discrete vortex numbers are diagnostic, not hard constraints: vortex entry/exit,
phase slips, pin occupancy, and hole winding can change through amplitude
suppression. The nonconvex optimization over both amplitude and phase is the task.

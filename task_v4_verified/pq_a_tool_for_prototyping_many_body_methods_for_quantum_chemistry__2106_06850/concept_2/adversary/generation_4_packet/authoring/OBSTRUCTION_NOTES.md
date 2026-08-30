# Private obstruction investigation

No universal infeasibility result is established. Optimizer floors are observations,
not lower-bound certificates, and the frozen task evaluates finite neighboring
roots rather than imposing a bound on the derivative at the base.

## Why a density-only argument does not settle the task

The Fock-restoring counterterm makes every Hamiltonian derivative vanish between
the reference determinant and its singles. A symmetric reference-single response
therefore has zero measured signed-energy gradient while changing the one-particle
spectrum. `obstruction_audit.json` gives an explicit linear relaxation with
violation 0.02 and DAD zero. That response is not a stationary biorthogonal CCSD
state, so it neither proves feasibility nor excludes a stronger CCSD obstruction.

## Numerical state relaxations

We minimized the 120-coordinate signed-energy-error gradient over CCSD right
amplitudes and lambda coefficients, omitting the Hamiltonian stationarity and
ground-connection constraints. Exact right-state and nearby physical ground-state
variants retain density, amplitude, lambda, reference-weight, and fidelity bounds.
The nearby-state relaxations reach approximately 0.1020343 at the exact target
and DAD bounds, on either population branch. These repeated local optima are not
globally certified minima. In particular they do not prove the finite-probe task
impossible even though they exceed the linearized scale 0.1.

## A genuine exclusion of one relaxed state

In the 20-determinant sector write `R=exp(T)|reference>`,
`L=(<reference|+lambda<SD|)exp(-T)`, and `n=<triple|exp(-T)`.
Then `L R=1`, `L_triple=0`, and `n R=0`. Exact CCSD and lambda stationarity imply

```
(H-E) R = z |triple>
L (H-E) = y n
```

For a normalized, gapped exact ground vector `psi`, let `e=E-E0`,
`a=psi.T R`, and `b=L psi`. When `psi_triple` and `n psi` are nonzero,
Hermiticity gives `z=-e*a/psi_triple` and `y=-e*b/(n psi)`. Compression of
`H-E0` to the span of `R` and the column corresponding to `L` then requires

```
e B >= gap G
B11 = R.T R - a*R_triple/psi_triple
B22 = L L.T - b*(n L.T)/(n psi)
B12 = B21 = 1
G11 = R.T R - a*a
G22 = L L.T - b*b
G12 = G21 = 1-a*b
```

For the stored near-optimal relaxed state, `B11` is about -15.75 and `B22`
about +5.46, whereas both diagonal elements of `G` are strictly positive.
Thus a positive exact gap would require both signs of `e` at once. Independent
exponentials reproduce these signs. The inverse-Hamiltonian optimization
accordingly collapses to a degenerate zero-gap state. This excludes that fixed
relaxed state, **not** the full Hamiltonian domain. State-variable searches with
this additional necessary compression constraint remain nonconvex.

Pure-state canonical-form results for three fermions in six orbitals do not
directly establish a theorem for the symmetrized biorthogonal lambda density.
Primary background checked: arXiv:1306.2570 and arXiv:1602.00578. Neither source
supplies the numerical obstruction needed here. No paper claim or task threshold
is changed by this private investigation.

# Disclosed generative law — generation 1

`distribution.py` is authoritative. Every split uses the same code and continuous
parameter distributions with independent random streams. Every split has exactly
one quarter of its rows in each family, then shuffles rows. Within each family,
`L` is independently 10 or 12 with probability 1/2: these are spatial sites,
corresponding to 20 or 24 spin orbitals. Public train/validation seeds are
84620915 and 91002031; hidden entropy is withheld.

Draw independent `U0 ~ Uniform(2,8)`, disorder amplitude `W ~ Uniform(0,2.5)`,
dimerization `delta ~ Uniform(0,0.5)`, rung ratio `r ~ Uniform(0.6,1.4)`, diagonal
ratio `f ~ Uniform(0.15,0.65)`, interaction heterogeneity `eta ~ Uniform(0,0.2)`,
and `phase ~ Uniform(0,2*pi)`. Every listed bond receives its own independent
multiplier `Uniform(0.9,1.1)`. Unused latent parameters are not supplied as features.

Canonical geometries before random site relabelling:

- **0, dimerized_ring:** edges `(j,(j+1)%L)`, strength `1+delta*(-1)^j`.
- **1, open_ladder:** two legs of length `ell=L/2`; site `(leg,c)` has index
  `leg*ell+c`. Leg edges between columns `c,c+1` have strength `1+delta*(-1)^c`
  for `c=0..ell-2`. Every rung `(0,c)-(1,c)` has strength `r`.
- **2, triangular_ladder:** the open ladder plus diagonals `(0,c)-(1,c+1)`
  of strength `f`, for `c=0..ell-2`. The triangles frustrate antiferromagnetic exchange.
- **3, periodic_ladder:** the open ladder plus a closing edge on each leg of
  strength `1+delta*(-1)^(ell-1)`, with no diagonals. Five-site periodic legs
  are frustrated odd cycles; six-site legs are even cycles.

For each canonical site `j`, draw independent `z_j,q_j ~ Uniform(-1,1)`.
Set `v_j=W*(0.6*cos(2*pi*j/L+phase)+0.4*z_j)` and subtract its site mean.
Set `U_j=U0*(1+eta*q_j)`. Uniformly permute all active sites, transforming
hopping, interaction and potential consistently. Pad 10-site arrays to width
twelve with zeros only after permutation. The code fixes the order of RNG calls.

No label-dependent rejection, extrapolation-only split, per-instance IDs, latent
seeds, or repeated Hamiltonians across splits are used. A family index represents
physical geometry, not an instance identifier. Numerical labels retain signed
energy differences, including tiny negative roundoff; they are not clipped.

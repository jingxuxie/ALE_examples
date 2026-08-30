# Disclosed generative distribution, version 1

`distribution.py` is authoritative and provided so there is no hidden convention.
Training, validation and private test use independent random streams, the same
code, parameter ranges and precision. Each split has exactly one quarter of its
rows in each family, then shuffles rows. Within every family, `L` is independently
8 or 10 with probability 1/2. These are 8–10 **spatial** sites (16–20 spin orbitals).
The train/validation seeds are 31957041 and 27068011; hidden entropy is withheld.
All random choices below are independent unless the formula states otherwise.

Draw `U0 ~ Uniform(2,8)`, disorder amplitude `W ~ Uniform(0,2.5)`, dimerization
`delta ~ Uniform(0,0.5)`, rung ratio `r ~ Uniform(0.6,1.4)`, diagonal ratio
`f ~ Uniform(0.15,0.65)`, interaction heterogeneity `eta ~ Uniform(0,0.2)`, and
`phase ~ Uniform(0,2*pi)`. Unused parameters are drawn but not supplied as features.
Every listed bond gets an independent multiplier `Uniform(0.9,1.1)`.

Canonical geometries before random site relabelling:

- **0, dimerized_ring**: edges `(j,(j+1)%L)` of strength `1+delta*(-1)^j`.
- **1, open_ladder**: two legs of length `ell=L/2`; site `(leg,column)` has index
  `leg*ell+column`. Leg edges `(leg,c)-(leg,c+1)` have strength
  `1+delta*(-1)^c`, `c=0..ell-2`. Each rung `(0,c)-(1,c)` has strength `r`.
- **2, triangular_ladder**: the open ladder plus `(0,c)-(1,c+1)` of strength
  `f` for `c=0..ell-2`. These triangles frustrate the antiferromagnetic exchange.
- **3, periodic_ladder**: the open ladder plus one closing edge on each leg,
  of strength `1+delta*(-1)^(ell-1)`; no diagonals. For length five, the odd
  periodic legs are themselves frustrated and bond alternation has a seam.

For canonical site `j`, draw `z_j,q_j ~ Uniform(-1,1)` and set
`v_j = W*(0.6*cos(2*pi*j/L+phase)+0.4*z_j)`, then subtract the site mean.
Set `U_j = U0*(1+eta*q_j)`. Generate a uniform random permutation of the active
sites and apply it consistently to hopping, interaction, and potential.
Pad 8-site arrays with zeros at the end to width ten, after the permutation.

No sorting by gaps, rejection by gap size, extrapolation split, repeated
Hamiltonians across splits, or label-dependent sampling is used. Each labelled
row is generated from a full Hamiltonian, not from a latent scalar lookup table.
The exact construction draws iid bond noise before onsite noise, as in the code.

The charge response involves different particle-number sectors; the spin response
can vary sharply with geometry and frustration even at similar charge gaps.
All-family and paired-observable scoring prevents one good observable or one
easy family from compensating for another. Permutation-invariant inputs or
covariant intermediate representations are encouraged.

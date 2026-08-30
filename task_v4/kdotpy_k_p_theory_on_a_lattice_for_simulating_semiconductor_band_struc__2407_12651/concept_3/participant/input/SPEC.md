# Model and witness contract

All energies and hoppings are dimensionless. Momentum is the full torus
`(kx,ky) in [-pi,pi)^2`. Generation 2 targets the lowest band of the full 4-by-4
matrix defined below. Its active block is `H_A = s I + dx sigma_x + dy sigma_y
+ dz sigma_z`. Both remote orbitals and every intermediate eigenstate are retained.
No continuum k.p cutoff or projected two-band approximation is permitted in scoring.

Let `A_pq = sin(p kx) cos(q ky)` and `B_pq = cos(q kx) sin(p ky)`.
The ordered spin modes are `p=1,2,3`, then `q=0,1,2,3`, omitting `(1,0)`.
For even modes use `p=1,2,3`, then `q=0,...,p`. Define
`F_pp = cos(p kx) cos(p ky)` and, for `p!=q`,
`F_pq = cos(p kx) cos(q ky) + cos(q kx) cos(p ky)`.
The complete explicit mode lists are in `model.json`.

For nominal coefficients `a,b,c,m`, the manufactured model is

```
dx = (1+v) sin(kx) + sum a_pq (1+alpha_pq) A_pq
dy = (1-v) sin(ky) + sum a_pq (1+alpha_pq) B_pq
dz = m+u + sum b_pq (1+beta_pq) F_pq
s  = sum c_pq (1+gamma_pq) F_pq
```

Here `u in [-0.05,0.05]`, `v in [-0.06,0.06]`, and **each** alpha, beta, gamma is
independently in `[-0.004,0.004]`. These are spatially uniform manufacturing errors;
the same coefficient error is shared across the members of its symmetry orbit.
There is no assumption that an adversary samples a particular distribution.
The box includes its boundary and all combinations. The evaluator's private
stress points add no restrictions to this public set.

The full fixed model, in basis `(E,H,E_remote,H_remote)`, is

```
H4 = [[H_A, V], [V^dagger, diag(5.5, 8.0)]]
c = cos(kx)+cos(ky)
p_minus = sin(kx)-i sin(ky)
p_plus = sin(kx)+i sin(ky)
V = [[1.1+0.25*c, 0.45*p_minus],
     [0.30*p_plus, 0.5+0.10*c]]
```

Remote levels and hybridizations are fixed, exact model constants. All previously
specified errors act on H_A only. No additional errors or controls are hidden.
At u=v=0 with zero coefficient errors, the C4 rotation satisfies
`H4(-ky,kx)=D H4(kx,ky) D^dagger`, `D=diag(1,i,1,i)`; thus the fixed remote model
does not introduce an anisotropy that the symmetry-orbit controls cannot compensate.
The prescribed v error intentionally breaks this symmetry just as in generation 1.

The two nominal fundamental sine coefficients are exactly one: the energy scale
is fixed and uniform rescaling is not an allowed operation. There is no scalar
onsite term. All hoppings have `|Rx|,|Ry|<=3`; no extra Fourier terms are permitted.
`m in [-1.9,-0.3]`, `|a|<=0.75`, `|b|<=1.5`, `|c|<=0.75`. At most eight of the 29
entries across a,b,c may be nonzero. A nonzero value of any magnitude counts;
neither rounding nor a hidden sparsity tolerance is used. The mass is not counted.

Submit exactly the keys `schema_version`, `mass`, `spin_orbit`, `orbital_mass`,
`scalar`, with version 1 and arrays of lengths 11,9,9. JSON duplicate keys,
booleans as coefficients, NaN/Infinity, strings, unknown keys, and oversized files
are invalid. The schema is structural; this document and model.json also impose
the sparsity and coefficient bounds.

For any fixed error vector order all four eigenvalues `E0(k)<=E1(k)<=E2(k)<=E3(k)`. Define
`W=max_k E0-min_k E0`, `g_direct=min_k(E1-E0)`, and
`g_indirect=min_k E1-max_k E0`. Acceptance concerns the largest W and smallest
gaps over the entire error box. There is no band below the target band.

Topology uses normalized lower eigenvectors and links
`Ux(k)=<u(k)|u(k+dx)>/abs(<u(k)|u(k+dx)>)`, similarly Uy. Sum the principal phases
of `Ux(k) Uy(k+dx) conj(Ux(k+dy)) conj(Uy(k))`, divided by `2*pi`, over the torus.
Increasing kx then ky defines orientation. This convention gives C=-1 for the
baseline mass -1 model. The checker anchors C=-degree using the uncoupled core's
d/|d|, then certifies a gapped coupling homotopy to the full four-band model.
The manufacture box is connected, so a globally certified nonclosing direct gap
extends the nominal invariant to every manufactured model by straight homotopy.

Score, for valid input and certified C=-1, is
`min(1, 0.175/W_cert, g_direct_cert/3, g_indirect_cert/3)`, clipped below at zero.
All three inequalities must pass; a rounded display score of one is not a pass.
Certificate failure or a wrong invariant scores zero. The task is a witness
problem: no claim of global optimality of the submitted design is required.

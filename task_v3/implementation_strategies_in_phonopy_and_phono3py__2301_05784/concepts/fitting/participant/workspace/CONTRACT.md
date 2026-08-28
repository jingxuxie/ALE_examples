# Array and geometry contract, version 1

## Invocation and files

Run `python solve.py INPUT.npz OUTPUT.npz`. Read with
`numpy.load(INPUT, allow_pickle=False)`. Write an NPZ containing `fc2` and `fc3`;
both must be finite float64 arrays of the exact shapes below. Additional output
arrays are ignored. Inputs have no object arrays. All atom and Cartesian
indices are zero-based. A scalar has NumPy shape `()`, not `(1,)`.

The interface example has the same schema as the larger inputs, but does not
represent their computational scale. A process has at most 180 seconds and
8192 MiB unless its execution environment explicitly grants more. NumPy and
SciPy can be used. No force-constant fitting package is required by the
interface.

## Units, signs, and axes

Cell rows are lattice vectors in angstrom. `positions2` and `positions3` are
fractional **row** coordinates in their respective supercells. Positions are
equilibrium positions; `u2` and `u3` are Cartesian displacements in angstrom,
not fractional displacements. `f2` and `f3` are Cartesian forces in
eV/angstrom, in exactly the same atom order as the corresponding positions.
`numbers2` and `numbers3` are atomic numbers, not species IDs or masses.

For a full harmonic tensor H and full cubic tensor C, the convention is

```
F[i,a] = -sum(j,b, H[i,j,a,b] * u[j,b])
         -0.5 * sum(j,k,b,c, C[i,j,k,a,b,c] * u[j,b] * u[k,c]).
```

Thus `fc2` has units eV/angstrom^2 and `fc3` eV/angstrom^3. Cartesian axes are
the supplied global Cartesian axes, not axes along the lattice vectors.
The factor one half applies to the full ordered sum over BOTH displaced atom
indices, including diagonal entries.

## Input inventory

Let N2 and N3 be the harmonic and cubic supercell atom counts, P the number of
translational representatives, M2 and M3 the training snapshot counts, and G2
and G3 the numbers of supplied point-operation representatives.

| Key | dtype | shape | Meaning |
| --- | --- | --- | --- |
| `schema_version` | int64 | `()` | Always 1. |
| `fit_mode` | int64 | `()` | 0: joint same-cell fit; 1: two-stage different-cell fit. |
| `u2`, `f2` | float64 | `(M2,N2,3)` | Harmonic training data; M2 is zero in mode 0. |
| `u3`, `f3` | float64 | `(M3,N3,3)` | Mixed second-plus-third-order training data. |
| `cell2`, `cell3` | float64 | `(3,3)` | Supercell lattice matrices. |
| `positions2`, `positions3` | float64 | `(N2,3)`, `(N3,3)` | Fractional equilibrium positions. |
| `numbers2`, `numbers3` | int64 | `(N2,)`, `(N3,)` | Atomic numbers. |
| `p2s2`, `p2s3` | int64 | `(P,)` | Supercell index of each compact representative. |
| `s2p2`, `s2p3` | int64 | `(N2,)`, `(N3,)` | Dense compact row index, in `[0,P)`. |
| `compact_map2`, `compact_map3` | int64 | `(N2,N2)`, `(N3,N3)` | Translation to each leading atom's representative frame. |
| `rotations2`, `rotations3` | int64 | `(G2,3,3)`, `(G3,3,3)` | Fractional rotation matrices. |
| `translations2`, `translations3` | float64 | `(G2,3)`, `(G3,3)` | Fractional translations paired with rotations. |
| `cart_rotations2`, `cart_rotations3` | float64 | `(G2,3,3)`, `(G3,3,3)` | Orthogonal Cartesian rotations. |
| `permutations2`, `permutations3` | int64 | `(G2,N2)`, `(G3,N3)` | Forward atom permutation for each operation. |
| `fold2to3` | int64 | `(P,N2)` | Harmonic alias-sum mapping into the cubic cell. |
| `cutoff3` | float64 | `()` | Cubic pair-distance cutoff in angstrom. |
| `triplet_mask3` | bool | `(P,N3,N3)` | Allowed cubic atom triplets. |

Output shapes:

```
fc2.shape == (P, N2, 3, 3)
fc3.shape == (P, N3, N3, 3, 3, 3)
```

## Compact indexing and translations

`s2p` contains dense row indices, NOT supercell representative indices.
`s2p[p2s[p]] == p`. Representatives belong to translation orbits, not complete
space-group orbits: symmetry-equivalent atoms related by a rotation can still
have different compact rows.

For each leading supercell atom i, `compact_map[i]` is a permutation of all
atoms. It applies the periodic translation taking i to `p2s[s2p[i]]`.
In particular, `compact_map[i,i] == p2s[s2p[i]]` and a representative's row is
the identity permutation. Full tensors are defined, without ambiguity, by

```
H[i,j,a,b] = fc2[s2p2[i], compact_map2[i,j], a,b]
C[i,j,k,a,b,c] = fc3[s2p3[i], compact_map3[i,j],
                    compact_map3[i,k], a,b,c].
```

Expanding C is unnecessary. To contract the compact row for leading atom i,
put displacements in that representative frame using
`u[:, argsort(compact_map3[i]), :]`, not `u[:, compact_map3[i], :]`.
These two permutations need not be equal.

## Different supercells

P has the same meaning and ordering in both cells. In mode 1, N2 can be 512
while N3 is 64. Never substitute an N3 harmonic tensor for the required N2
output. The harmonic tensor acting on cubic-cell displacements is the alias
sum

```
small_fc2[p,k,a,b] = sum(fc2[p,j,a,b]
                         for j if fold2to3[p,j] == k).
```

Expand `small_fc2` using `s2p3` and `compact_map3`. `fold2to3[p,j]` identifies
the atom in cell 3 equivalent to atom j of cell 2 after aligning representative
p in cell 2 with representative p in cell 3. The alignment includes the
representative-position offset and periodic wrapping. Contributions are
SUMMED, not averaged. In mode 0, the two cells and representative orderings
are identical and the folding map is the identity in every row.

## Fitting objective

The unknowns must obey the invariances and cubic support restriction below.
Use the supplied raw forces; do not invent zero-displacement observations,
add an intercept, change units, or replace observed forces with harmonic
surrogates. A global force drift or higher-order remainder is real residual
error, not an extra output degree of freedom.

In **mode 0**, fit fc2 and fc3 jointly by minimizing the sum of squared errors
of the mixed-force equation on `(u3,f3)`. No separate harmonic observations
are present. Do not estimate fc2 and then hold an unconstrained harmonic-only
fit fixed: this can absorb the cubic signal.

In **mode 1**, first minimize harmonic-only squared force error on `(u2,f2)`
over fc2, subject to its invariances. Then hold that fc2 fixed, fold it to
cell 3, subtract its predicted harmonic forces from `f3`, and fit fc3 to the
remaining mixed-force residual. This two-stage objective is intentional:
the supplied cells and observation counts differ. The harmonic observations
can themselves have small anharmonic or numerical residuals.

Squared errors include all training snapshots, all supercell atoms and all
three force components, with equal weight. No ridge penalty is specified.
If a constrained least-squares system is rank deficient, use its
minimum-Euclidean-norm tensor solution. The central cases are chosen to
identify the symmetry-allowed unknowns. Numerical regularization should not
overwhelm the cubic signal.

## Invariances and finite-range support

For full tensors, the harmonic permutation is
`H[i,j,a,b] == H[j,i,b,a]`. The cubic tensor is unchanged by any simultaneous
permutation of the three `(atom,Cartesian)` index pairs. Swapping only atom
indices, or only Cartesian indices, is incorrect.

Acoustic sum rules require summing over any one atom index while fixing all
other indices to give zero. For example, `sum(j,H[i,j,a,b]) == 0` and
`sum(k,C[i,j,k,a,b,c]) == 0`. They are separate from, and must coexist with,
permutation and crystal symmetry.

For operation g with fractional rotation Rf and translation t,

```
fractional_position[permutations[g,i]]
    == fractional_position[i] @ Rf.T + t    (mod integer translations)
Rcart = cell.T @ Rf @ inv(cell.T)
```

The arrays `cart_rotations` supply Rcart directly. With Q = Rcart and pi the
forward atom permutation, covariance means

```
H[pi[i],pi[j],a,b] = sum(d,e, Q[a,d]*Q[b,e]*H[i,j,d,e])
C[pi[i],pi[j],pi[k],a,b,c]
    = sum(d,e,f, Q[a,d]*Q[b,e]*Q[c,f]*C[i,j,k,d,e,f]).
```

One operation is supplied for each distinct fractional rotation. Together
with all pure translations represented by the distinct `compact_map` rows,
these generate the complete supercell space group. Fractional rotations
need not be orthogonal under the ordinary Cartesian dot product.

`triplet_mask3[p,j,k]` is true precisely when every pair among
`(p2s3[p],j,k)` has minimum-image distance no greater than `cutoff3`, with
1e-8 angstrom numerical slack. Set all 27 Cartesian entries to zero where
the mask is false. There is no harmonic cutoff. Distances and the mask are
based on the original supercell geometry, not displaced snapshots. The
provided mask is authoritative at numerical boundaries.

## Evaluation

Both tensors are compared with independently computed constrained fits.
Unseen original force snapshots test harmonic predictions where applicable
and mixed predictions in every case. The evaluator also checks acoustic,
permutation, space-group, and support residuals. A submission must work on
previously unseen snapshot selections and multiple structure families.
No hidden basis, expected tensors, force-test observations, or calibration
data are supplied to the solver.

# NPZ contract, version 1

Scoring normalizes each branch error by its measured starter error, with
relative-error scale floors of 1e-5 for derivatives and 1e-6 for mode response.
Thus scientifically negligible errors are not amplified merely because the
starter is already very accurate on an easy input. Scores remain continuous.

All NPZ files are readable with `numpy.load(..., allow_pickle=False)`. Inputs use
float64, complex128, int64, or Boolean arrays; there are no object arrays.
Indices are zero based. Atomic Cartesian components are flattened in the order
`3*atom + component`. Let A be the number of primitive atoms and M=3A.

## Outcome 1: full polar derivative

Input arrays:

| key | shape | meaning |
|---|---|---|
| `schema_version` | scalar | integer 1 |
| `cell` | (3,3) | primitive lattice vectors as rows, Angstrom |
| `positions` | (A,3) | Cartesian atomic positions, Angstrom |
| `masses` | (A,) | atomic masses, AMU |
| `born` | (A,3,3) | Born tensor Z[atom, electric-field axis, displacement axis] |
| `dielectric` | (3,3) | symmetric positive-definite electronic dielectric tensor |
| `nac_factor` | scalar | already includes the electrostatic unit conversion and 4*pi/volume |
| `ewald_lambda` | scalar | Gaussian reciprocal-sum scale |
| `g_vectors` | (G,3) | finite Cartesian reciprocal lattice vectors, cycles/Angstrom |
| `sr_vectors` | (T,3) | Cartesian shortest-image displacement vectors, Angstrom |
| `sr_i`, `sr_j` | (T,) | destination atom-block row/column |
| `sr_blocks` | (T,3,3) | short-range coefficients, ALREADY mass normalized and divided by image multiplicity |
| `q_cart` | (Q,3) | derivative queries, Cartesian cycles/Angstrom |

Vectors are rows in stored arrays. The reduced coordinate is `q_cart @ cell.T`.
No reciprocal vector contains a hidden 2*pi. Define the M by M matrix

    D(k) = HermitianPart(S(k) + P(k)) + constant,
    S[i,a; j,b](k) = sum over t with (sr_i[t],sr_j[t])=(i,j)
                     sr_blocks[t,a,b] exp(2*pi*i*k dot sr_vectors[t]),
    Qg = g_vectors[g] + k,
    B = Qg dot dielectric dot Qg,
    phase[i,j,g] = exp(2*pi*i*g_vectors[g] dot (positions[i]-positions[j])),
    P[i,a; j,b](k) = nac_factor / sqrt(masses[i]*masses[j])
                    * sum_g phase[i,j,g] exp(-B/(4*ewald_lambda**2))
                    * (sum_c Qg[c]*born[i,c,a])
                    * (sum_d Qg[d]*born[j,d,b]) / B.

Here `HermitianPart(X)=(X+X.conj().T)/2`. The omitted constant is independent
of k and does not affect the answer. The supplied short-range coefficients
already have the long-range part subtracted; do NOT subtract it again. The phase
in P depends on g, not Qg. G and the Gaussian scale stay fixed during the
derivative. Sum every supplied reciprocal vector. There is no frequency cutoff
in this outcome. Queries exclude exact reciprocal-lattice singularities; the
minimum `norm(g+k)` is at least 2e-5 cycles/Angstrom in this pilot.

Required output `derivative`, complex128, shape **(Q,3,M,M)**, is the derivative
of the complete D with respect to Cartesian k. The derivative index precedes
the two flattened atom/component indices. Its units are the input dynamical
matrix units times Angstrom. Both short-range and dipole contributions count.

## Outcome 2: independent degenerate-mode Cartesian response

These are independent matrix packets, not the `q_cart` queries above. They
provide all information needed for the second outcome.

| key | shape | meaning |
|---|---|---|
| `response_ddm_reduced` | (P,3,M,M) | Hermitian derivatives with respect to REDUCED q coordinates |
| `response_eigenvalues` | (P,M) | eigenvalues lambda of the dynamical matrix, ascending |
| `response_eigenvectors` | (P,M,M) | orthonormal eigenvectors as COLUMNS, possibly complex |
| `response_groups` | (P,M) | contiguous integer group labels; different labels never mix |
| `response_active` | (P,M) | whether the group has a usable positive frequency; constant within a group |
| `response_directions` | (K,3) | Cartesian unit directions; the first three are x,y,z |
| `frequency_factor` | scalar | positive conversion factor f[THz]=factor*sqrt(lambda) |
| `branch_tolerance` | scalar | absolute tolerance for unresolved directional slopes, Angstrom*THz |

Within each declared group use its mean eigenvalue lambda_B. Declared groups
come from actual degeneracies up to numerical diagonalization tolerance.
The basis within a group is arbitrary; columns are not individual physical
branches until a perturbation direction is specified. For a Cartesian
perturbation dk, the reduced perturbation is `dq = cell @ dk` in column notation.

For active group B, define the first-order frequency response operator H_B by

    f_B(k + dk) = f_B(k)*I + sum_mu dk[mu]*H_B[mu] + O(norm(dk)**2),

where the dynamical matrix perturbation is restricted to the supplied columns
of that group before taking the positive square-root frequency function.
Thus the normalization is `frequency_factor/(2*sqrt(lambda_B))`, and the
restriction uses the complex adjoint of those eigenvector columns. This
specifies the operator, not an arbitrary diagonal in a chosen basis.

Required output `response`, complex128, shape **(P,3,M,M)**, contains H_B in the
original supplied eigenvector basis, inserted at each group's row/column
indices. Cross-group entries and inactive-group entries must be zero.

Required output `velocity`, float64, shape **(P,K,M)**, contains the eigenvalues
of `sum_mu response_directions[direction,mu]*H_B[mu]`, sorted ascending WITHIN
each group and placed in that group's slots. Inactive slots are zero. These
are directional velocity spectra; do not align mode labels across different
directions. Units are Angstrom*THz, equivalent to 100 m/s per unit. No extra
2*pi conversion is applied. This definition remains unambiguous even when a
direction leaves a degeneracy unresolved.

Required output `branch_velocity`, float64, shape **(P,K,M,3)**, gives the
Cartesian velocity vector in the branch basis selected by EACH direction.
Within an active group, choose an orthonormal basis that diagonalizes its
directional H, ordered by ascending directional eigenvalue. The Cartesian
components are the diagonal matrix elements of all three H operators in
that SAME direction-selected basis; independently diagonalizing each Cartesian
operator is not this answer. To remove ambiguity when directional eigenvalues
remain tied, group adjacent sorted slopes whose successive gap is at most
`branch_tolerance`. Replace each Cartesian component throughout that tied
cluster by its arithmetic mean (equivalently the trace divided by cluster size).
Inactive slots are zero. Directional spectra and direction-selected Cartesian
vectors are distinct outputs. Complex eigenvector phases never change either.

## Output and diagnostics

All four required arrays must be finite and have exactly the shapes stated.
Extra numeric scalar diagnostic arrays are allowed and ignored for correctness.
The starter reports times and cumulative process peak RSS after each branch;
these self-reported values are NOT trusted scoring inputs. External execution
time and RSS are recorded by the evaluator. Any conforming numerical method,
including a sufficiently accurate finite-difference implementation, is allowed.

# Array contract, version 1

All inputs and outputs are NumPy NPZ archives loadable with `allow_pickle=False`. No object arrays. Energies and Hamiltonians use eV; the real-space cell uses angstrom. Reduced vectors are row vectors. The orbital basis is orthonormal and its order must not change. Spin, when present in a supplied Hamiltonian, is already included in the orbital index; do not multiply conductance by two.

## Input

| Key | Shape / type | Meaning |
| --- | --- | --- |
| `schema_version` | scalar integer `1` | Schema version |
| `h_R` | `(nhop,3)` integer | Directed lattice translations, including zero |
| `h_matrices` | `(nhop,norb,norb)` complex | **Full**, not half, Hamiltonian blocks; both conjugate directions are supplied |
| `cell` | `(3,3)` real | Primitive lattice vectors as rows |
| `orbital_positions` | `(norb,3)` real | Orbital centers in reduced primitive coordinates |
| `cells` | `(ncell,3)` integer | All finite-device primitive-cell tags; no periodic identification |
| `potential` | `(ncell,norb)` real | Additional onsite potential, in `cells` order |
| `energies` | `(nenergy,)` real | Real scattering energies; use the retarded limit, not a user-chosen artificial broadening |
| `lead_count` | scalar integer, 2 or 3 | Number of contacts |
| `lead_cells_j` | `(ncell_j,3)` integer | Ordered principal-layer cells inside the finite device, constituting lead `j`'s interface |
| `lead_period_j` | `(3,)` integer | Translation from that interface **outward** into the semi-infinite lead |
| `lead_shift_j` | scalar real | Uniform onsite shift for the periodic lead |

The integer `j` runs from zero to `lead_count-1`. Cases contain no family labels or solutions.

## Finite geometry and lead convention

For device cell tags `a,b` and orbitals `i,j`,

```text
H_device[(a,i),(b,j)] = H[b-a][i,j]
                     + delta_ab delta_ij potential[a,i].
```

An absent translation has a zero block. Exclude a hopping if either cell is absent. Do not add a second conjugate to the full input blocks. Position `(a + orbital_positions[i]) @ cell` fixes the physical embedding; it does not add a Bloch phase to this real-space Hamiltonian. Gates are already evaluated at those positions in `potential`.

For interface tags `q_a`, period `p`, and `n_j=ncell_j*norb`, flatten in **the supplied `lead_cells_j` order, then orbital order**. Define

```text
H0[(a,i),(b,j)] = H[q_b-q_a][i,j] + delta_ab delta_ij lead_shift
B [(a,i),(b,j)] = H[q_b-q_a-p][i,j].
```

`B` is `H(outward layer, inward layer)`, not its adjoint. Layers are `q + m*p` for `m=0,1,...`; `m=0` is the already-present device interface and `m>=1` is the lead exterior. The input principal layers are large enough that only adjacent layers couple. They are deliberately not assumed minimal: `B` can have an exact nullspace without the physical lead being disconnected. Lead interfaces do not overlap, and every hopping between a device cell and that lead's exterior touches its stated interface. All other cut boundaries are open. Separate leads have no mutual coupling outside the device.

Let the retarded surface Green function of layer `m=1` be `g`. In this convention,

```text
g = inverse((E+i0) I - H0 - B^dagger g B)
Sigma = B^dagger g B
Gamma = i (Sigma-Sigma^dagger) is positive semidefinite.
```

These equations specify the branch, not a required algorithm. A direct inverse of `B` is invalid for the provided singular leads. The requested selfenergy acts on the complete ordered `m=0` interface, including rows with no direct outward coupling.

## Output

Write every following key. Set `nlead=lead_count`, `nmax=max_j(n_j)`. All fields except `sigma_j` are real; `mode_counts` may be integer or numerically exact real. Additional keys are ignored.

| Key | Shape | Definition |
| --- | --- | --- |
| `sigma_j` | `(nenergy,n_j,n_j)` complex | Retarded selfenergy in the ordered interface basis above |
| `mode_counts` | `(nenergy,nlead)` | Number of incoming propagating channels in each lead |
| `transmission` | `(nenergy,nlead,nlead)` | `T[out,in] = trace(S[out,in]^dagger S[out,in])`; diagonal entries are reflection probabilities summed over channels |
| `channels` | `(nenergy,nlead,nlead,nmax)` | For `out != in`, squared singular values of the flux-normalized scattering block, descending, followed by zeros to `nmax`. Retain `min(N_out,N_in)` values, including true zeros. For `out == in`, the whole vector is zero by convention. |
| `partition_noise` | `(nenergy,nlead,nlead)` | Off-diagonal `sum(tau*(1-tau))`; diagonal zero by convention |
| `lb_conductance` | `(nenergy,nlead,nlead)` | `C[out,in] = delta_out,in N_in - T[out,in]`, in `e^2/h` units |

For two terminals, `partition_noise[1,0]` is the dimensionless zero-temperature shot-noise factor. For three terminals, the specified pair factor corresponds to one biased injecting contact; it is **not** the complete multi-contact noise-correlation tensor. The full transmission/conductance matrices are required, including the side lead. Columns of `transmission` sum to the corresponding incoming mode count. The Landauer–Büttiker matrix has zero row and column sums for these coherent, current-conserving cases.

The selfenergy tolerance does not authorize changing the model with a finite imaginary onsite term. Energies avoid exact mode thresholds. Normalization floors in scoring prevent near-zero noise or evanescent matrix entries from dominating; matching only transmission traces is insufficient to recover eigenchannels or noise.

## Continuous score

Each valid field has unbounded normalized error `||prediction-reference||_F / (||reference||_F + floor*sqrt(number_of_entries))`. Missing, invalid, nonfinite, or incorrectly shaped fields receive zero credit. Selfenergy errors are averaged over leads. The groups `(selfenergy, mode_counts, transmission, channels, partition_noise, lb_conductance)` have weights `(0.25,0.10,0.20,0.20,0.15,0.10)` and floors `(0.05,1.0,0.01,0.001,0.005,0.01)` respectively.

Valid group score is `1/(1 + 9*error/max(baseline_error,1e-8))`, without clipping or a tolerance plateau. The calibration uses dimensionless unit errors for the missing transport capability; a separate zero-transport control is measured as a weak numerical baseline. The case score is the weighted group average. Family scores average their cases; the core score averages families equally and the worst-family score is reported separately. This is continuous error reduction, not a count of tolerance passes.

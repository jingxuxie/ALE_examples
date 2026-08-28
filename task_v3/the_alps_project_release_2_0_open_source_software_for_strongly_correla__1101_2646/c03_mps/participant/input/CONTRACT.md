# Model and interface contract

One invocation processes one UTF-8 JSON object. All numbers are real, all sites are zero-indexed, all boundaries are open, and hbar = 1. The energy is TOTAL energy, not energy per site. There is no thermodynamic-limit extrapolation. Couplings in the input fix the energy unit.

## Shared fields

- `family`: `spin1_chain`, `spinhalf_ladder`, or `bose_hubbard`.
- `length`: total number of sites, including both legs for a ladder.
- `bonds`: list of explicitly enumerated bonds. Count every listed bond exactly once. The ordering is significant only for identifying the sites, not an extra multiplicity.
- `observables`: ordered list of objects with `kind` and `sites: [left, right]`, where `left < right`.
- Spin cases also contain `spin`, `single_ion`, `field`, `ground_sector`, and `excited_sector`.
- Boson cases also contain `nmax`, `interaction`, `potential`, and `particles`.

All site arrays have `length` elements. Do not infer uniformity or substitute a lattice average. Expected hidden sizes are 32--80 sites; small examples and checks can be shorter.

## Spin models

The Hamiltonian is

```
H = sum_bonds [ jxy/2 * (Splus_i Sminus_j + Sminus_i Splus_j)
                + jz * Sz_i Sz_j ]
    + sum_i single_ion[i] * Sz_i^2 - sum_i field[i] * Sz_i.
```

A spin bond is `{"sites": [i,j], "jxy": value, "jz": value}`. The local eigenvalues of `Sz` are `-spin, -spin+1, ..., spin`, and
`Splus |m> = sqrt(spin*(spin+1)-m*(m+1)) |m+1>`.
`Sx = (Splus + Sminus)/2`. In particular spin-half operators are Pauli matrices divided by TWO, not Pauli matrices.

`ground_sector` and `excited_sector` are values of TOTAL Sz in these physical units. `energy` is the lowest energy at `ground_sector`; `gap` is the lowest energy at `excited_sector` MINUS `energy`. This is a sector energy difference, not a request for the globally first excited state.

### Spin-one chain

`family = spin1_chain`, `spin = 1`, nearest-neighbor bonds only. Parameters explore the gapped spin-one regime with positive exchange, mild dimerization, site anisotropy, and weak longitudinal fields. Typically `ground_sector = 0`, `excited_sector = 2`. The latter avoids confusing the almost-degenerate open-chain edge multiplet with a bulk-scale excitation; the finite-system definition above is authoritative.

Observable kinds:

- `zz`: `<Sz_left Sz_right>` (not connected).
- `string`: `-<Sz_left [product_(left<k<right) exp(i*pi*Sz_k)] Sz_right>`. Endpoints are EXCLUDED from the product, and the leading minus sign is part of the definition. For neighboring sites the product is the identity.

### Inhomogeneous spin-half ladder

`family = spinhalf_ladder`, `spin = 0.5`, even `length`. Site `2*r + a` labels leg `a in {0,1}` of rung `r`. Rungs join `(2*r,2*r+1)` and legs join `(2*r+a,2*(r+1)+a)`. The supplied bond list is complete. Rung and leg couplings need not agree, and neither couplings nor longitudinal fields need be uniform. Typically `ground_sector = 0`, `excited_sector = 1`.

Observable kinds:

- `zz`: `<Sz_left Sz_right>` (not connected).
- `xx`: `<Sx_left Sx_right>`.

Hidden spin exchange strengths are between 0.5 and 2.5, `jz/jxy` between 0.85 and 1.2, spin-one single-ion coefficients between -0.25 and 0.55, and longitudinal fields have magnitude at most 0.12. These are ranges, not a promise of arbitrary graphs or additional phases.

## Truncated Bose-Hubbard chain

```
H = -sum_bonds hopping * (bdag_i b_j + bdag_j b_i)
    + sum_i interaction[i]/2 * n_i*(n_i-1)
    + sum_i potential[i] * n_i.
```

A boson bond is `{"sites": [i,j], "hopping": value}`. Only nearest-neighbor bonds occur. The on-site basis is `0,...,nmax`; `b |n> = sqrt(n) |n-1>`, and `bdag |nmax> = 0`. This finite local cutoff is part of the DEFINITION of the model, not a numerical tolerance to extrapolate away. `potential` enters with the PLUS sign shown; it is not a chemical potential with the opposite sign.

`energy` is the lowest energy at total particle number `particles`. Write `E(number)` for the ground energy in that number sector. `gap = E(particles+1) + E(particles-1) - 2*E(particles)`.

Observable kinds, all measured in the `particles` ground state:

- `one_body`: real part of `<bdag_left b_right>`; do not add its Hermitian conjugate.
- `density_connected`: `<n_left n_right> - <n_left>*<n_right>`.

Hidden cases have `nmax` 3 or 4, unit mean filling, hopping 0.75--1.25, repulsive interaction 4--8, and site potentials of magnitude at most 0.8.

## Output

```
{"energy": -12.345, "gap": 0.123, "correlations": [0.04, -0.03]}
```

The example numbers above are illustrative only. `correlations` must have the same length and order as `observables`. Every value must be finite and real. Extra diagnostic fields are allowed and ignored. Create the output file at the supplied path; stdout is not the answer.

Energies, sector gaps, and each correlation kind receive separate continuous accuracy scores. Correlations are not normalized by a tiny nearly-zero individual reference value. Both average and worst-family performance are reported. An unhandled case scores zero; the wall-clock cutoff is a feasibility bound, not a speed competition.

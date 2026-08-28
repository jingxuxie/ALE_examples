# Model and measurement contract

All sites are physical spatial electronic orbitals with two spin modes, up
(index 0) and down (index 1). The electronic mode convention is
`0-up,0-down,1-up,1-down,...`. The fermion anticommutation relations are exact.
An oscillator, if present, is a separate bosonic degree of freedom, commuting
with all fermions. Units set hbar=1 and the reference hopping scale to 1.

Prepare the lowest-energy normalized pure state of `H_before` in `sector`.
At time zero quench instantaneously to time-independent `H_after`, and evolve
unitarily. This is a finite closed system at zero temperature, not a Lindblad
or externally replenished reservoir calculation. `sector.kind` specifies the
actual allowed space: `number_sz` fixes total N and twice Sz; `number` fixes N
but not Sz; `parity` fixes only N modulo 2. The value is NOT a chemical potential.
Do not impose an additional conservation law absent from the model.

For stage `before` or `after`, the Hamiltonian consists of:

- `onsite[stage][i] * (n_i_up + n_i_down)`;
- `zeeman[i] * (n_i_up - n_i_down)/2`, if supplied;
- `interaction[i] * n_i_up * n_i_down` (the coefficient is the full U);
- for each edge with sites `[i,j]`,
  `sum_ab edge[stage][a][b] * c†_(i,a) c_(j,b) + Hermitian conjugate`;
- for each pairing record with sites `[i,j]` and spins `[a,b]`,
  `pair[stage] * c†_(i,a) c†_(j,b) + Hermitian conjugate`, in that order;
- `density_edges`: `strength * n_i * n_j`, where n is spin-summed;
- each oscillator contributes
  `omega * b†b + coupling[stage] * (n_site - offset) * (b† + b)`.

A complex scalar is encoded `[real,imaginary]`. Every edge/pairing record
already implies its Hermitian conjugate; records are not an adjacency matrix
to be symmetrized a second time. Onsite opposite-spin pair records are allowed,
as are same-spin pairs on distinct sites. Spin-orbit edges may mix spins.
Oscillator `levels` means occupation 0 through levels-1. The finite truncation
is part of the model; do not substitute a classical oscillator or change its
cutoff silently. Oscillator zero-point energies are NOT included.

`layout` lists a proposed tensor ordering of physical degrees of freedom:
electrons are 0 through n_sites-1 and oscillators follow in the order of
`phonons`. This is a numerical suggestion, not a relabeling of Hamiltonian
indices. You may choose a better order. Measured quantities always refer to
the original physical site indices, not tensor positions. `family` is a
descriptive annotation only; the records and sector define the problem.

The five experiment classes are: interacting impurity chains; doped interacting
ladders with diagonal and density interactions; flux rings with spin-orbit
hopping; paired interacting wires; and Hubbard-Holstein-like vibrational
contacts. The input graphs and coefficients, rather than assumptions about a
family name, are authoritative. All hidden inputs obey these definitions.

## Output columns

All expectations except norm are divided by the actual state norm.

- `norm`: the actual propagated state squared norm, before any reporting-only
  normalization. Deliberate normalization during propagation is allowed but
  must be disclosed and cannot replace accuracy checks.
- `charge`: Q = sum of spin-summed electron occupations in `region`.
- `number`: total electronic occupation N, not counting oscillators.
- `spin`: total Sz = (N_up-N_down)/2.
- `phonon`: sum of oscillator occupations; zero when no oscillators exist.
- `energy`: expectation of H_after, including all supplied terms, at every t.
- `current`: inward transport rate into `region`, contributed by all hopping
  terms. Its sign is fixed by `i * [H_hopping,Q]`, not a preferred bond direction.
- `source`: the inward regional electron creation/destruction rate contributed
  by pairing, `i * [H_pairing,Q]`. This is distinct from transport current.

The continuity statement is d<Q>/dt = current + source. The latter is not
generally zero for paired models. Energy is conserved after the quench. Total
N and Sz are conserved only where the Hamiltonian has those symmetries.
`initial_energy` in stats.json is the energy of H_before, before the quench.

For a tiny exact calibration: two sites, two electrons, Sz=0, one real diagonal
hopping edge with amplitude -1, U=2 on each site, and no other terms have ground
energy `1-sqrt(5)`. At equilibrium each site has charge 1, total N=2, Sz=0,
and both regional current and pairing source are zero. This is a calibration,
not a substitute for the development study.

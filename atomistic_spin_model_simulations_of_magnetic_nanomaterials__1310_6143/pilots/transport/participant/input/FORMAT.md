# Physical and I/O contract (version 1)

Invocation: `python solve.py CASE.json OUTPUT.json`. JSON only; NPZ is not an accepted submission format. The process must write exactly one JSON object to the given output path. Extra stdout is ignored. Binary64 calculations are recommended. NaN, infinity, missing keys, wrong shapes, and failed processes are invalid.

## Input

- `version`: integer 1; `case_id`: opaque identifier, not a physical parameter.
- `num_sublattices`: positive integer K. Labels are zero-based.
- `voltage_V`: nonnegative voltage magnitude; `direction`: either +1 or -1.
- `cell_length_m`, `cell_area_m2`: positive length along a stack and transverse area, shared by all cells.
- `stacks`: disjoint lists of consecutive cell IDs, each in increasing physical-z order. Their union is `0..C-1`. They are connected electrically in parallel. Cells within a stack are connected in series. Direction -1 exchanges the entrance and exit of every stack; voltage and reported currents remain magnitudes along that selected direction.
- `materials`: objects with `sublattice`, `rho_ohm_m`, `rho_spin_ohm_m`, `moment_muB`, `alpha`, `eta`, and `beta`.
- `atoms`: objects with `cell`, `material`, and `spin` (three Cartesian components, unit norm). Output atom order is exactly this list order, which need not follow cells, materials, or sublattices.

Every atom is magnetic: moment and ordinary resistivity are strictly positive. Spin resistivity is nonnegative. All cells contain atoms. Every sublattice is occupied at both endpoints of each stack, but may be absent inside. All material labels are valid. No periodic stack wraparound, nonmagnetic-remove path, spin diffusion, inter-stack lateral currents, stochastic dynamics, or exchange/anisotropy fields are included.

## Physical conventions

For an occupied cell-sublattice, let n be its atom count, N the whole-cell atom count, f=n/N, and M the sum of its atomic moments in muB. The reduced magnetization is `m=sum(moment*spin)/M`; do not normalize this reduced vector to unit length. Resistivities and alpha/eta/beta are arithmetic atom-count means within that cell-sublattice. Its ordinary and spin resistance parameters in ohms are respectively `r=mean(rho)*L/(f*A)` and `q=mean(rho_spin)*L/(f*A)`.

The entrance cell uses ordinary resistances only and has zero transport field. At any later occupied channel the upstream polarization p is the reduced magnetization of the most recent occupied cell of the same sublattice in the selected direction. Missing channels do not reset p. The channel's resistance is `r + q*(1-dot(m,p))/2`. An absent channel is an open channel, not a zero-ohm resistor: its current and field are zero. All occupied channels within one cell share that cell's voltage drop. Report the resulting series/parallel resistances and branch-current magnitudes. Current conservation is local to each cell: the sum over its channel currents equals its stack current, including the entrance.

The occupied channel's transport effective field in tesla is

`H = 35486911.9121 * (I_channel/M) * [(eta-alpha*beta)*(m cross p) + (beta+alpha*eta)*p]`.

The decimal constant is the fixed convention for hbar/(2*e*muB); do not replace it with a rounded estimate. Every atom receives its own cell-sublattice's H, including when atomic spins within that channel differ. For each atom, report the transport-only instantaneous derivative

`dspin_dt = -gamma/(1+alpha_atom^2) * [spin cross H + alpha_atom*(spin cross (spin cross H))]`,

with `gamma=1.760859e11 rad/(s*T)`. This is a tangent derivative, not an integrated spin or a magnetic moment torque. There is no additional atomic-moment division here. All fields/derivatives at entrance atoms are zero. Other interactions and thermal noise are excluded.

## Output

All keys below are required; each array uses the original global IDs/order.

| key | shape | units |
|---|---|---|
| `total_resistance_ohm` | scalar | ohm |
| `total_current_A` | scalar | ampere |
| `stack_resistance_ohm` | P | ohm |
| `stack_current_A` | P | ampere |
| `cell_resistance_ohm` | C | ohm |
| `channel_current_A` | C by K | ampere |
| `atom_field_T` | number of atoms by 3 | tesla |
| `atom_dspin_dt` | number of atoms by 3 | 1/second |

## Limits and evaluation

Cases may contain up to 16 stacks, 512 cells, 8 sublattices, 64 materials, and 50,000 atoms. The outer wall-time limit is 90 seconds per case, including isolation setup. Separately, the submission command must finish within 20 seconds as measured inside the sandbox by `/usr/bin/time` (`compute_seconds`, elapsed time rather than pure CPU time). The address-space cap is 1 GiB. Missing timing or exceeding either execution budget makes the output invalid. Runtime is otherwise reported separately, not rewarded by changing the physical score. Four equally weighted groups evaluate resistance, currents, atomic field, and spin derivative using relative RMS errors. Normalization floors are 1e-12 ohm, 1e-18 ampere, 1e-18 tesla, and 1e-7 inverse seconds respectively. A continuous exponential score is calibrated to the starting baseline on a frozen initial set; calibrations remain fixed for larger sets. Only input and submission files, an output directory, and a system runtime are exposed in strict sandbox mode.

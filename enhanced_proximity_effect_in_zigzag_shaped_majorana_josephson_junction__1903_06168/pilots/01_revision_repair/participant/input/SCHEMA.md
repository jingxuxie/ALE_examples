# Request and result schema (version 1)

One UTF-8 JSON object per request; no batch protocol, filenames, or case identifiers
carry model semantics. Required top-level fields are `version` (1), `kind`
(`barrier` or `gap`), `geometry`, and `model`.

## Geometry

Required keys: `W`, `L_x`, `L_sc_up`, `L_sc_down`, `z_x`, `z_y`, `a`,
`transverse_soi`, `mu_from_bottom_of_spin_orbit_bands`, `k_x_in_sc`, `infinite`.
Lengths are in nm; flags are booleans. This pilot uses the historical `sawtooth`
shape, including its straight limit `z_y=0`. `wraparound` equals `infinite`.
`L_x` is an integer multiple of both `a` and `z_x`. The source's half-open
coordinate slices, floor divisions in the normal-width offset, eight-neighbor
edge predicates, flood-fill starting sites, and barrier/normal/top/bottom fill
order are part of the model. Do not substitute a continuum-width approximation
or silently change the hopping assignment at interfaces.

Supported bounds: `8 <= a <= 12`, `6*a <= W <= 12*a`,
`6*a <= z_x <= 12*a`, `0 <= z_y <= 2*a`,
`2*a <= L_sc_up,L_sc_down <= 5*a`, `L_x <= 2*z_x`.
Evaluated devices contain at most 600 lattice sites (2,400 orbitals).
There are four spin/Nambu orbitals per site. No external superconducting leads,
rough edges, orbital magnetic field, or particle-hole removal are requested.

## Model

All keys are required, finite, real numbers:

| Keys | Meaning / units |
| --- | --- |
| `mu`, `V`, `Delta_left`, `Delta_right` | Chemical potential, barrier strength, pair amplitudes; meV |
| `alpha_middle`, `alpha_left`, `alpha_right` | Spin-orbit coefficients; meV nm |
| `g_factor_middle`, `g_factor_left`, `g_factor_right` | Dimensionless Zeeman factors, with the source's normalization |
| `B_x`, `B_y`, `B_z` | Magnetic field; tesla |
| `phase` | Relative pairing phase; radians |

Use the constants and basis in `workspace/upstream/zigzag.py`.
Here `left` denotes the top superconductor and `right` the bottom one.
Hidden requests stay within `0 <= mu <= 8`, `0 < V <= 12`,
`0.2 <= Delta_left,Delta_right <= 1.2`, `0 <= alpha_* <= 25`,
`0 <= g_factor_* <= 15`, `0 <= B_x <= 1`, `B_y=B_z=0`,
and `0 <= phase <= pi`. Geometry may be finite or periodic for `barrier`;
`gap` always uses an x-periodic, wrapped unit cell.

## Barrier response

A `barrier` request also has `probes`: 1–600 distinct integer pairs `[ix,iy]`
specifying lattice tags, not physical coordinates. It may include tags absent
from the device. At dimensionless Bloch momentum zero, let `H(V)` and `H(0)`
be the assembled Hamiltonians with all other parameters unchanged. For each
probe return

`Re(trace((I_spin ⊗ tau_z) @ (H(V)[site,site] - H(0)[site,site]))) / (4*V)`.

Return zero for absent sites. The result is an onsite Hamiltonian response,
not the outer edge of a continuum drawing. Output:

```json
{"version": 1, "response": [0.0, 1.0]}
```

The array must have exactly the supplied probe order and length.

## Excitation gap

A `gap` request also has `grid_points` (an odd integer from 17 to 65).
Return the minimum absolute eigenenergy of the wrapped Hamiltonian over
`0 <= k_x <= pi`, in meV. Momentum is dimensionless per unit cell, not nm^-1.
`grid_points` is the supplied initial search resolution, not a promise that the
minimum lies on that grid. Resolve an interior minimum as well as endpoints.
The pool excludes unresolved competing minima and exact gap closings.

```json
{"version": 1, "gap": 0.125}
```

These numbers illustrate shape only; they are not expected sample answers.
Additional output keys are ignored. No explanations, timings, site counts, or
source patches are graded. Scoring is continuous in response RMSE or absolute
gap error, normalized against an executable unrepaired baseline. Strong
numerical agreement approaches 1; the calibration baseline scores about 0.01.
Families have equal weight. Runtime and protocol failures are reported separately.

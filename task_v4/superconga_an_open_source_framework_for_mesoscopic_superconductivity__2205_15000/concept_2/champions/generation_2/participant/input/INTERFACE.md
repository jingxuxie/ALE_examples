# Device and artifact contract

Run the baseline with
`python3 baseline/solve.py --input input --output OUTPUT_DIRECTORY`.
Import `workspace/spectral.py` for `load_problem`, `validate_design`,
`hamiltonian`, `response`, and `discrepancies`.

`pattern` is a binary vector in the exact `candidates` order. A one denotes a
normal metallic inclusion at that site, not a removed electron site. The
superconducting complement must be connected by horizontal/vertical bonds.
The number of ones is exactly `normal_site_count`. Coordinates are `[x,y]`,
zero-based, with electron index `y*width+x`; all boundaries are open.

The electron Hamiltonian has onsite `-mu + pin_potential*pattern`, nearest
and diagonal hopping as given in the device file, and symmetric-gauge Peierls
phases. `flux` is in electron flux quanta through the rectangular device.
Pairing is externally prescribed: positive `gap_d` on horizontal bonds,
negative on vertical bonds, `+i*gap_xy` on rising diagonals, and
`-i*gap_xy` on falling diagonals. Pairing on any bond touching an inclusion is
zero. The condition's `pair_scale` multiplies all remaining pairing. The
Hamiltonian in the electron/up-hole/down Nambu block is
`[[h, D], [D.conj().T, -h.conj()]]`. It is a finite lattice model; there is no
unmentioned continuum extrapolation, gap iteration, screening, or impurity
self-energy. Energies and hopping are dimensionless.

`response(config, pattern)` returns `[condition, probe, energy]` electron LDOS,
using all eigenvalues with the positive Lorentzian broadening in `device.json`.
The published `target.npz` contains this shape as `ldos`. Continuous patterns
are accepted by the forward model for experimentation but not as artifacts.

Each probe/condition error is normalized by the RMS of its target spectrum
(floored at 0.02). The core error is the RMS over all samples. Each condition
error is its own RMS. A score is `max(0, 1 - error/score_scale)`; the worst-family
score is the minimum over conditions. Pass thresholds are in TASK.md. Both
positive and negative energies matter. Scoring recomputes the spectra from
the artifact; claimed spectra or scores are ignored. The fingerprint is known
to have at least one fabrication-feasible realization, which is not supplied.

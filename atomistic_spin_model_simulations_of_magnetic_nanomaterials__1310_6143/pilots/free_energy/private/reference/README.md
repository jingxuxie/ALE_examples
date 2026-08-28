# Privileged reference and provenance

## Primary sources

Official source: https://github.com/richard-evans/vampire

Pinned commit: `525bc27ee44c525aee229570f30f3d4c61d54f66`.

- `src/montecarlo/cmc.cpp`, beginning line 283, complete `cmc_step()`:
  https://github.com/richard-evans/vampire/blob/525bc27ee44c525aee229570f30f3d4c61d54f66/src/montecarlo/cmc.cpp#L283
- `src/montecarlo/mc_moves.cpp`, beginning line 71, complete `mc_angle()`:
  https://github.com/richard-evans/vampire/blob/525bc27ee44c525aee229570f30f3d4c61d54f66/src/montecarlo/mc_moves.cpp#L71
- Constrained-MC derivation, Asselin et al., algorithm in Section III and
  Appendix A, particularly Eq. A11: https://arxiv.org/abs/1006.3507
- Parent atomistic-spin implementation paper: https://arxiv.org/abs/1310.6143

`extract.py` extracts the two complete functions without changing their bodies.
`provenance.json` gives original and extracted SHA-256 values. Associated source
licenses are retained. Shared official source is read-only and was not modified.

In the frame where the constrained moment points along +z, the constrained pair
move uses the acceptance ratio

```
min(1, exp(-DeltaH/T) * (Mz_new/Mz_old)^2 * abs(sjz_old/sjz_new)).
```

The magnetization-length and compensating-spin Jacobians distinguish the target
solid-angle directional ensemble from a Cartesian transverse-delta ensemble.
The unchanged official function also rejects infeasible compensating spins and
reversed total magnetization. The adapter selects the official fixed-width
Gaussian angular move; production does not use adaptive proposals.

## Dependency and unit adapter

`engine.cpp` supplies arrays, equal atomic moments, a standard `mt19937_64` RNG,
the graph Hamiltonian, rotation matrices, and observable collection. It does
not reimplement the constrained transition kernel. Material temperature
rescaling is disabled. The official driver's conversion is cancelled by

```
T_official = 1000*T
mu = 9.27400915e-24
energy_return = H_local * 1000*kB / (mu*mu*1.07828231e23)
kB = 1.3806503e-23
```

so its exponent is exactly `DeltaH/T` up to floating-point rounding. The native
inspector checks this cancellation against independent dimensionless local
energies. Full energy counts each undirected bond once, while local move energy
includes every incident bond. Torque is `sum(s cross (-dH/ds))_y/N`; rigid y
rotation gives `d(H/N)/dtheta = -torque`.

The C++ driver emits blocks of 200 sweeps, measuring every five sweeps. A sweep
is the official function's N attempted pair updates. Frozen-node gold begins
with four independently seeded chains, 3,000 equilibration sweeps and 10,000
production sweeps. Alternating chains first spend 2,000 sweeps at T=1.4.
`refinement_plan.json` identifies convergence-triggered replacements with four
fresh chains, 10,000 equilibration and 30,000 production sweeps. Original raw
chains and their failing audit remain available.

All 17-node midpoint chains use separate seeds, 6,000 equilibration and 10,000
production sweeps. The independent strong solution uses two other hot-started
chains, 6,000 equilibration and 10,000 production sweeps at each of seven interior
output angles. Strong seeds are disjoint from all gold and validation seeds.

The SEM is the maximum of between-chain SEM and blocked within-chain SEM.
R-hat is computed on block means for torque, moment length, and internal energy.
Angular integration propagates the independent-angle covariance linearly.
Gold uses seven sine modes over 17 angles; strong uses four modes over nine.
`angular_refinement.json` propagates shared-node covariance when comparing grids.
Reflection and endpoint tests use independent trajectories, not values set to
zero by the output symmetry convention.

## Reproduction

Run from the pilot root. No global dependency installation is needed.

```
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$PWD/participant/workspace/vendor"
g++ -std=c++17 -O3 -DNDEBUG private/reference/engine.cpp -o private/reference/official_reference
python private/reference/generate.py --workers 48
python private/reference/extend.py
python private/reference/dense.py
python private/reference/generate.py --aggregate-only
python private/reference/refine_angles.py
g++ -std=c++17 -O3 -DNDEBUG private/reference/inspect_state.cpp -o private/reference/inspect_state
python private/reference/independent_checks.py
python private/reference/calibrate.py
python private/reference/seal.py
```

Raw jobs are cached by case/kind/angle/chain. To recompute rather than reuse,
archive the entire `raw/` directory before running generation. The case manifest
is already frozen: do not regenerate or retune cases during participant trials.
`cases.py` documents their construction but is not part of evaluator execution.
Changing source/parameters requires a new provenance seal and reference run;
cached raw filenames alone do not detect a changed Hamiltonian or source.

See root `README.md` for approximation limits and exposure boundaries. No
accuracy claim should be separated from the validation reports or uncertainty.

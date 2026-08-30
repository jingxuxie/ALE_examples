# Bounded private generation-four investigation

Outcome: no passing witness and no universal impossibility proof.
Main owns the empirical fresh-attempt and final status decision; no readiness/status file was changed.

## Scope and isolation

Only generation-four `authoring/` was changed. No active v4/v4_r2 submission or source was read, and no agents were launched.
All 20 frozen public/trusted source hashes remain intact. Historical generation-three snapshot/champion hashes also match.
Elapsed bounded investigation: 38.48 wall minutes.

## Search evidence

The state-level portfolio contains 310 multistarts. These are relaxations/local searches, not global bounds.
Exact-target nearby-state searches observed gradient norm about 0.1020343 on both population branches; no minimum was globally certified.
Hamiltonian-only implicit derivatives, actual two-neighbor optimization, and simultaneous three-root stationarity searches used only completed old witnesses or private seeds.
Two direct finite-probe searches reached best three-point maximum energy errors 0.000213831157864 and 0.00021871203153; the target remains 0.0001.
These are search diagnostics, not accepted full-stencil witnesses. Exact scorer results, including any other failures, are in `portfolio_certification_final.json`.

## Obstruction evidence

An exact rational certificate excludes one near-optimal relaxed tuple from every exactly stationary CCSD/Hermitian positive-gap realization: opposite signs of two Rayleigh coefficients demand opposite signs of the energy error.
The certificate is restricted to that stored tuple. It is not a universal theorem over the task domain; see `OBSTRUCTION_NOTES.md` and `exact_relaxed_state_exclusion.json`.
Neither a global gradient lower bound nor the additional finite-curvature bound needed for a finite-probe impossibility result was established.

## Independent checks

- finite_author: pass=False, core=0.0, reason=robust_constraints_failed, runtime=4.642s.
- finite_v3: pass=False, core=0.0, reason=robust_constraints_failed, runtime=4.081s.
- reduced_gen1: pass=False, core=0.0, reason=robust_constraints_failed, runtime=4.412s.
- reduced_r2: pass=False, core=0.0, reason=robust_constraints_failed, runtime=3.922s.
- joint_scaled_author: pass=False, core=0.0, reason=robust_constraints_failed, runtime=3.767s.
- joint_scaled_v3: pass=False, core=0.0, reason=robust_constraints_failed, runtime=3.698s.
- known_gen3_private_seed: pass=False, core=0.0, reason=robust_constraints_failed, runtime=3.853s.

`private_derivative_audit.json` validates the private smooth search surrogate. Every artifact is evaluated with the unchanged exact frozen DAD and strict JSON/path checker.
The initial zero-DAD nondifferentiability audit is retained separately; no frozen oracle, evaluator, threshold, or manifest was changed to accommodate it.

All source, logs, state relaxations, candidate snapshots, and reports are private to this directory.

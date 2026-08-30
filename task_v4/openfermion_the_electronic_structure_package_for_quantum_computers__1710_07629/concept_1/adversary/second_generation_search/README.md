# Contingent private pool for a later champion audit

This directory is exploratory provenance only. It creates no participant
generation, changes no frozen directory, and neither reads fresh outputs nor
evaluates any contender. If the current fresh attempt fails, do not turn this
pool into another task by default.

The pool contains 24 independent Hamiltonians with n=14/16 and r=12/14, from
the same two-frame localized PSD charge construction used by generation 1.
There are three secondary-strength regimes and four independent seeds per
dimension/regime combination. Charge support width, factor scales, relative
strengths, and near-block auxiliary mixing stay within the retained law/ranges.
All new parent seeds differ from the prior pool. One-particle-sector spectra
exclude public regaugings and same-dimension duplicates within the new pool.

Run `prepare.py --cpu 187 --cpu-budget 720`. BLAS is single-threaded, the
process is pinned away from CPU 188, and an OS CPU limit caps it at 900 seconds.
The existing trusted optimizer searches both gauges from planted, spectral,
interpolated, and perturbed starts. Round-robin optimization and atomic saved
witnesses preserve coverage if the optimization budget is exhausted.

## Artifacts and reference semantics

- `cases.json`: unscored physical pool. `baseline_cost` is deliberately absent
  until actual champion reference costs can be calibrated under authorization.
- `optimizer_inputs.json`: PRIVATE optimizer inputs. Its `baseline_cost` is
  original spectral scaling only, never a champion reference or task score.
- `private_solution.json` and `private_references.json`: valid gauge witnesses
  and independently checked absolute costs, not claimed global optima.
- `config.json`, `provenance.json`, and `planted_starts.json`: seeds, ranges,
  generation details, PSD/locality/tensor identities, physical spectra, and starts.
- `optimization_history.json`: CPU accounting and each trusted optimization run.
- `rootcause_clusters.json`: ex-ante physical strata, not proven failure clusters.
- `source_hashes.json` and `report.json`: frozen-source checks and readiness limits.

No hardness or extra-compression gap can be claimed before a completed champion
is evaluated through the authorized trusted sandbox. A future task must retain
the disclosed 10*N resource limit and use genuine champion reference costs.

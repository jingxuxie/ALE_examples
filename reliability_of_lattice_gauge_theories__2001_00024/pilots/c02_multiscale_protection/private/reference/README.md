# Privileged many-body reference

This is a precomputed-output reference backed by existing tensor-network engines,
not recovered target-author source and not a new exact many-body algorithm.
`engine.py` uses quimb 1.10.0; `charge_engine.py` uses physics-tenpy 1.1.0.
Both receive the same explicitly specified open-chain Hamiltonian. The latter
conserves the exact alternating matter charge `sum((-1)**j * n_j)`, not the
individual Gauss generators broken by the coherent errors. Every local bond's
charge commutator is checked. The dangling right link remains dynamical.

Original records completed with quimb use bond ceilings 48/96 and time steps
0.025/0.0125. Subsequent TeNPy records use 64/128 with the same time steps.
Both use fourth-order evolution and independent coarse/fine truncation settings.
Records include runtime, truncation diagnostics, parameter-recovery checks, and
observable differences. Stored values use known generating calibration parameters;
independent fits verify that the stated small-cluster observations recover them
within their noise level. No large-chain label is used in calibration fitting.

Validation evidence includes:

- `small_system_validation.json`: quimb versus dense evolution for both spins.
- `charge_engine_final_geometry_validation.json`: TeNPy versus dense evolution,
  including an odd-length spin-one chain and corrected two-site geometry.
- `charge_checks/inhomogeneous_weak_18334.json`: independent large-chain
  TeNPy/quimb agreement, with maximum density difference below 1.8e-5.
- `*_convergence_audit.json`: per-family normalized coarse/fine differences.
- `all_initial_physical_checks.json`: all 21 frozen initial cases satisfy density,
  positivity, covariance, and alternating-charge checks; maximum charge residual
  is below 6.2e-9. Unvalidated high-entanglement transfer probes are excluded.

Coarse/fine agreement is a numerical convergence diagnostic, not a rigorous
error bound. A reference oracle scoring one against its own cached labels is only
an interface check; it is not used as independent evidence of scientific accuracy.

From the repository root, use the pinned author-only environment and run:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_CACHE_DIR=/tmp/ale_reference_numba python tasks_v3/reliability_of_lattice_gauge_theories__2001_00024/pilots/c02_multiscale_protection/private/reference/build.py --split screening --engine charge --workers 3 --bond 128
```

The other frozen split names are `challenge` and `confirmation`. Existing records
are preserved, not silently regenerated. A completed build assembles the private
`oracle/lookup.json`; the oracle and labels are never participant-visible. Hidden
evaluation runs submitted numerical code in a separate one-CPU, 6-GiB namespace.

All dense-state memory estimates in `authoring/dense_scale_audit.json` are computed
without allocating an infeasible array. Even a single full state at the minimum
public large-chain size exceeds the memory limit by many orders of magnitude.

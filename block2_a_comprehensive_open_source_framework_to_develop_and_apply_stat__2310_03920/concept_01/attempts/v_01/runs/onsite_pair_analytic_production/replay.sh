#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 1000000, "bond": 96, "sweeps": 14, "step": 0.15, "energy_tol": 1e-11, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-12, "krylov_tol": 1e-14, "spin_orbitals": true, "number_as_sz": false, "one_site_after": 0.25, "sparse_memory_limit_mb": 2600, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 96], "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "parity", "value": 0}, "sector_dimension": 2, "estimated_sparse_mb": 100.00172233581543, "method": "sector sparse diagonalization and exponential action"}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

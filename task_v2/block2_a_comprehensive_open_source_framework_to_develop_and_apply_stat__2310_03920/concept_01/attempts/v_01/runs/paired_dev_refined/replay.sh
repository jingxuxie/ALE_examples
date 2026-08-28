#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 1000000, "bond": 160, "sweeps": 20, "step": 0.075, "energy_tol": 1e-12, "eig_tol": 2e-13, "cutoff": 1e-18, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-12, "krylov_tol": 1e-14, "spin_orbitals": true, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "parity", "value": 0}, "sector_dimension": 2048, "estimated_sparse_mb": 103.9609375, "method": "sector sparse diagonalization and exponential action", "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 160]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" refined

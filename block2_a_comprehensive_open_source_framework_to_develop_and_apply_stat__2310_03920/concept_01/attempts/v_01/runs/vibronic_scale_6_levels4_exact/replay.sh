#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 2000000, "bond": 128, "sweeps": 14, "step": 0.1, "energy_tol": 1e-11, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-12, "krylov_tol": 1e-14, "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 3900, "initial_bond": 128, "bond_schedule": [128], "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 6, "twosz": 0}, "sector_dimension": 1638400, "estimated_sparse_mb": 3831.25, "method": "sector sparse diagonalization and exponential action"}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

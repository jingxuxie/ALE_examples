#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 600000, "bond": 128, "sweeps": 14, "step": 0.1, "energy_tol": 1e-11, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-15, "krylov_tol": 1e-18, "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 12, "twosz": 0}, "sector_dimension": 853776, "estimated_sparse_mb": 1604.6864013671875, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "symmetry_implementation": "specialized SZ", "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 128], "layout_override": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

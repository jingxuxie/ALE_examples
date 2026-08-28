#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 192, "sweeps": 20, "step": 0.05, "energy_tol": 1e-12, "eig_tol": 2e-13, "cutoff": 1e-18, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-17, "krylov_tol": 1e-20, "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 6, "twosz": 0}, "sector_dimension": 291600, "estimated_sparse_mb": 764.0823364257812, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11], "symmetry_implementation": "specialized SZ", "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 192], "layout_override": [0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" refined

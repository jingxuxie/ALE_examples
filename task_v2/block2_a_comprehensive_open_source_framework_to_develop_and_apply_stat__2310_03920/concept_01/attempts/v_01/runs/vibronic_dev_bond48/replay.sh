#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 48, "sweeps": 8, "step": 0.12, "energy_tol": 1e-08, "eig_tol": 1e-09, "cutoff": 1e-12, "optimize_layout": true, "general_symmetry": true, "davidson_tol": 1e-12, "krylov_tol": 1e-14, "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 4, "twosz": 0}, "sector_dimension": 9216, "estimated_sparse_mb": 116.2421875, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 4, 1, 5, 2, 6, 3, 7], "symmetry_implementation": "general Abelian", "initial_bond": 32, "bond_schedule": [32, 32, 48, 48, 48], "layout_override": [0, 4, 1, 5, 2, 6, 3, 7]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" baseline

#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 16, "sweeps": 24, "step": 0.12, "energy_tol": 1e-13, "eig_tol": 1e-09, "cutoff": 1e-12, "optimize_layout": false, "general_symmetry": true, "davidson_tol": 1e-12, "krylov_tol": 1e-14, "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 4, "twosz": 0}, "sector_dimension": 225, "estimated_sparse_mb": 100.35791397094727, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 1, 2, 3, 4, 5], "symmetry_implementation": "general Abelian", "initial_bond": 16, "bond_schedule": [16, 16, 16, 16, 16], "layout_override": [0, 1, 2, 3, 4, 5]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" baseline

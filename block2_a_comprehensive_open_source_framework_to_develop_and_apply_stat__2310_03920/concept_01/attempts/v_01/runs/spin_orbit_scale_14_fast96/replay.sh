#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 96, "sweeps": 14, "step": 0.1, "energy_tol": 1e-10, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number", "value": 12}, "sector_dimension": 30421755, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [2, 1, 3, 4, 0, 5, 6, 7, 13, 8, 9, 12, 10, 11], "symmetry_implementation": "general Abelian", "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 96], "general_symmetry": true, "layout_override": [2, 1, 3, 4, 0, 5, 6, 7, 13, 8, 9, 12, 10, 11]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

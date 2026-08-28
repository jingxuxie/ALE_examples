#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 96, "sweeps": 14, "step": 0.1, "energy_tol": 1e-10, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 10, "twosz": 0}, "sector_dimension": 260112384, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 10, 1, 11, 2, 12, 3, 13, 4, 14, 5, 15, 6, 7, 8, 9], "symmetry_implementation": "specialized SZ", "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 96], "general_symmetry": false, "layout_override": [0, 10, 1, 11, 2, 12, 3, 13, 4, 14, 5, 15, 6, 7, 8, 9]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

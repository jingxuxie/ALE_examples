#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 96, "sweeps": 14, "step": 0.1, "energy_tol": 1e-10, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "spin_orbitals": true, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "parity", "value": 0}, "sector_dimension": 524288, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], "symmetry_implementation": "general Abelian modes", "local_electronic_dimension": 2, "number_as_sz": false, "one_site_after": null, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 96], "general_symmetry": true, "mode_layout_override": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

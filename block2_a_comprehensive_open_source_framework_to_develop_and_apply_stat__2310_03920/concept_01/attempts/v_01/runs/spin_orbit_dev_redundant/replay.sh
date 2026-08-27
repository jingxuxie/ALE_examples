#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 128, "sweeps": 14, "step": 0.1, "energy_tol": 1e-10, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "number_as_sz": true, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number", "value": 4}, "sector_dimension": 495, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [3, 4, 2, 5, 1, 0], "symmetry_implementation": "specialized SZ with redundant (N,N), not physical Sz", "spin_orbitals": false, "one_site_after": null, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 128], "general_symmetry": true, "layout_override": [3, 4, 2, 5, 1, 0]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 16, "sweeps": 8, "step": 0.12, "energy_tol": 1e-08, "eig_tol": 1e-09, "cutoff": 1e-12, "optimize_layout": false, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 2, "twosz": 0}, "sector_dimension": 4, "method": "two-site DMRG and two-site TDVP", "tensor_layout": [1, 0], "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "initial_bond": 16, "bond_schedule": [16, 16, 16, 16, 16], "general_symmetry": true, "layout_override": [1, 0], "davidson_tol": 1e-12, "krylov_tol": 1e-14}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" baseline

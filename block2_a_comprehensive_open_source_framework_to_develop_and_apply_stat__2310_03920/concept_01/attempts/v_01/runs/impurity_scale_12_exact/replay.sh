#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 1000000, "bond": 160, "sweeps": 14, "step": 0.04, "energy_tol": 1e-10, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number_sz", "value": 12, "twosz": 0}, "sector_dimension": 853776, "method": "sector sparse diagonalization and exponential action", "spin_orbitals": false, "number_as_sz": false, "one_site_after": null, "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 160], "general_symmetry": true, "davidson_tol": 1e-12, "krylov_tol": 1e-14}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

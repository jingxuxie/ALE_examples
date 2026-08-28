#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_SETTINGS='{"exact_limit": 0, "bond": 160, "sweeps": 14, "step": 0.15, "energy_tol": 1e-11, "eig_tol": 2e-12, "cutoff": 1e-16, "optimize_layout": true, "general_symmetry": false, "davidson_tol": 1e-15, "krylov_tol": 1e-18, "spin_orbitals": false, "number_as_sz": true, "one_site_after": 0.25, "sparse_memory_limit_mb": 2600, "threads": 2, "seed": 1729, "normalization_during_evolution": false, "sector": {"kind": "number", "value": 4}, "sector_dimension": 495, "estimated_sparse_mb": 100.91486930847168, "method": "two-site DMRG and two-site TDVP; one-site TDVP after 0.25", "tensor_layout": [3, 4, 2, 5, 1, 0], "symmetry_implementation": "specialized SZ with redundant (N,N), not physical Sz", "initial_bond": 32, "bond_schedule": [32, 32, 64, 64, 160], "layout_override": [3, 4, 2, 5, 1, 0]}'
bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" production

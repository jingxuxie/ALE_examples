#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root/workspace"
python3 legacy_driver.py --cases "$root/inputs/controls.json" --output "$root/runs/baseline/controls" --config production
python3 legacy_driver.py --cases "$root/inputs/development.json" --output "$root/runs/baseline/development" --config production
python3 legacy_driver.py --cases "$root/inputs/controls.json" --output "$root/runs/baseline/refinement" --config conservative
python3 check_tests.py > "$root/runs/tests.jsonl"
python3 experiment.py --input "$root/inputs" --output "$root"
python3 qualification.py --input "$root/inputs" --output "$root"
python3 finalize.py --output "$root"
python3 audit_artifacts.py --output "$root" --replay

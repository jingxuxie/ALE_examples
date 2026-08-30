#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python fit.py --name plain --precondition 0 --seconds 1500 --iterations 1000 > plain.log 2>&1 &
plain_pid=$!
python fit.py --name density_half --precondition 0.5 --seconds 1500 --iterations 1000 > density_half.log 2>&1 &
half_pid=$!
python fit.py --name density_full --precondition 1 --seconds 1500 --iterations 1000 > density_full.log 2>&1 &
full_pid=$!
wait "$plain_pid" || true
wait "$half_pid" || true
wait "$full_pid" || true
python finalize.py

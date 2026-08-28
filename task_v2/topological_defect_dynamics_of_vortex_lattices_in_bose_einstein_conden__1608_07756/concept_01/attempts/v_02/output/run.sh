#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
root=$(cd "$(dirname "$0")" && pwd)
exec python "$root/workspace/cli.py" "$1" "$2" "${3:-$root/config.json}"

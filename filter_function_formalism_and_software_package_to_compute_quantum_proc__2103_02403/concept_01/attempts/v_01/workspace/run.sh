#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PYTHONPATH="$ROOT:$ROOT/vendor:$ROOT/deps"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
mkdir -p -- "${2:?Output directory required}/.runtime"
export NUMBA_CACHE_DIR="$(realpath -- "$2")/.runtime/numba"
export MPLCONFIGDIR="$(realpath -- "$2")/.runtime/matplotlib"
python -m pipeline.cli "$@"

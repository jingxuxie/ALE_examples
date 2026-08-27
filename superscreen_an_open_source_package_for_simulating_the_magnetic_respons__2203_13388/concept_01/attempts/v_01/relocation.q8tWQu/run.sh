#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
: "${ALE_RUNTIME:?Set ALE_RUNTIME to the supplied workspace/runtime directory}"
export PYTHONPATH="$ROOT/workspace:$ALE_RUNTIME"
export PYTHONNOUSERSITE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="$ROOT/.cache/matplotlib"
export NUMBA_CACHE_DIR="$ROOT/.cache/numba"
mkdir -p "$MPLCONFIGDIR" "$NUMBA_CACHE_DIR"
exec python -m qualification.cli "$@"

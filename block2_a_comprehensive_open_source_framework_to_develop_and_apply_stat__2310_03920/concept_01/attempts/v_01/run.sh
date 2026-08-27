#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${ALE_ASSETS:?Set ALE_ASSETS to the supplied read-only assets directory}"
mkdir -p "$2"
export TMPDIR="$2/tmp"
mkdir -p "$TMPDIR"
source "$ALE_ASSETS/workspace/env.sh"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$TMPDIR/matplotlib"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=2 OMP_NUM_THREADS=2
exec python3 "$HERE/workspace/solve.py" "$1" "$2" "${3:-production}"

#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ASSETS=${ALE_ASSETS:-$(cd "$HERE/../participant/v_01" && pwd)}
export PYTHONPATH="$HERE/workspace:$ASSETS/workspace/runtime"
export LD_LIBRARY_PATH="$ASSETS/workspace/runtime/lib:${LD_LIBRARY_PATH:-}"
LIBROOT="$ASSETS/workspace/runtime/block2.libs"
export LD_PRELOAD="$LIBROOT/libgomp-a34b3233.so.1.0.0:$LIBROOT/libmkl_core-a1f8e95a.so.1:$LIBROOT/libmkl_gnu_thread-76126a9d.so.1:$LIBROOT/libmkl_intel_lp64-eeafede9.so.1"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=2 OMP_NUM_THREADS=2
export MPLCONFIGDIR="${TMPDIR:-/tmp}/transport-mpl"
exec python3 "$HERE/workspace/solve.py" "$@"

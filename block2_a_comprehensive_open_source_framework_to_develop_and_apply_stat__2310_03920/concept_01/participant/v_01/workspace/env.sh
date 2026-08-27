#!/usr/bin/env bash
ASSET_WORKSPACE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export ALE_ASSETS=$(dirname "$ASSET_WORKSPACE")
export PYTHONPATH="$ASSET_WORKSPACE/runtime:${PYTHONPATH:-}"
export LD_LIBRARY_PATH="$ASSET_WORKSPACE/runtime/lib:${LD_LIBRARY_PATH:-}"
LIBROOT="$ASSET_WORKSPACE/runtime/block2.libs"
export LD_PRELOAD="$LIBROOT/libgomp-a34b3233.so.1.0.0:$LIBROOT/libmkl_core-a1f8e95a.so.1:$LIBROOT/libmkl_gnu_thread-76126a9d.so.1:$LIBROOT/libmkl_intel_lp64-eeafede9.so.1"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=2 OMP_NUM_THREADS=2
export MPLCONFIGDIR="${TMPDIR:-/tmp}/transport-mpl"

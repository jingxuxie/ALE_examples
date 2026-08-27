#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ -f "$HERE/workspace/cli.py" ]]; then
  exec python "$HERE/workspace/cli.py" "$@"
else
  exec python "$HERE/cli.py" "$@"
fi

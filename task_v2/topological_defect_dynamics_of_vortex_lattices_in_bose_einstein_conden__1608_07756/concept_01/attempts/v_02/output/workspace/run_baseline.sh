#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
root=$(cd "$(dirname "$0")" && pwd)
exec python "$root/cli.py" "$@"

#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $# -ne 2 ]]; then
  echo "Usage: bash run.sh request.json results_directory" >&2
  exit 2
fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$2/.build"
BUILD=$(cd -- "$2/.build" && pwd)
for PROGRAM in generate spectral; do
  if [[ ! -x "$BUILD/$PROGRAM" || "$HERE/workspace/$PROGRAM.cpp" -nt "$BUILD/$PROGRAM" ]]; then
    g++ -O3 -std=c++17 "$HERE/workspace/$PROGRAM.cpp" -o "$BUILD/$PROGRAM"
  fi
done
export GENERATOR_EXE="$BUILD/generate" SPECTRAL_EXE="$BUILD/spectral"
python3 "$HERE/workspace/experiment.py" "$1" "$2"

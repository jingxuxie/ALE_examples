#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INPUT="$(cd "${1:?Supply the development input directory}" && pwd)"
OUTPUT="${2:-$ROOT}"
mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
: "${ALE_RUNTIME:?Set ALE_RUNTIME to the supplied offline runtime}"
export PYTHONPATH="$ROOT/workspace:$ALE_RUNTIME"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export NUMBA_CACHE_DIR="$ROOT/.cache/numba" MPLCONFIGDIR="$ROOT/.cache/matplotlib" MPLBACKEND=Agg
bash "$ROOT/run.sh" suite "$INPUT/suite.json" "$OUTPUT" > "$OUTPUT/final_suite.log" 2>&1
python -m qualification.experiments "$INPUT" "$OUTPUT" > "$OUTPUT/experiments.log" 2>&1
RELOCATED="$(mktemp -d "$OUTPUT/relocation.XXXXXX")"
cp -a "$ROOT/workspace" "$RELOCATED/workspace"
cp "$ROOT/run.sh" "$RELOCATED/run.sh"
python - "$RELOCATED/run.sh" "$INPUT/dev_ring.npz" "$OUTPUT/raw/qualified/cold_dev_ring.npz" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
import time
start = time.perf_counter()
subprocess.run(['bash', sys.argv[1], 'case', sys.argv[2], sys.argv[3]], check=True)
path = Path(sys.argv[3]).with_suffix('.metrics.json')
metrics = json.loads(path.read_text())
metrics['process_wall_seconds'] = time.perf_counter() - start
path.write_text(json.dumps(metrics, indent=2))
PY
python -m qualification.finalize "$OUTPUT"
python -m qualification.audit "$INPUT/suite.json" "$OUTPUT" > "$OUTPUT/audit.log"
python -m pytest "$ROOT/workspace/tests" -q -o "cache_dir=$OUTPUT/.pytest_cache" > "$OUTPUT/tests.log"

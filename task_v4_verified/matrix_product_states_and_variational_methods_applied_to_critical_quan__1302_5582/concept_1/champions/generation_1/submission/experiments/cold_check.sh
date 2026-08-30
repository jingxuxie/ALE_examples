#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
budget="${1:-6}"
python - "$budget" <<'PY'
import json
import sys
from pathlib import Path
from experiments.benchmark import cases
for request in cases():
    request['budget_seconds'] = float(sys.argv[1])
    request['wall_seconds'] = 30.0 if float(sys.argv[1]) <= 6 else 120.0
    Path('experiments/cold_' + request['case_id'] + '.json').write_text(json.dumps(request))
PY
for request in experiments/cold_*.json; do
    state="${request%.json}.npz"
    echo "$request"
    (ulimit -t "$budget"; ulimit -v 2097152; /usr/bin/time -f 'cpu_user=%U cpu_system=%S wall=%e maxrss_kib=%M' python solve.py --request "$request" --output "$state")
    python contractor.py --request "$request" --state "$state"
done

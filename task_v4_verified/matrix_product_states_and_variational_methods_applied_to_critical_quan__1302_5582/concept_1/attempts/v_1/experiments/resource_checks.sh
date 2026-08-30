#!/bin/bash
set -u
cd "$(dirname "$0")/.."
mkdir -p experiments/requests experiments/states experiments/timings
python - <<'PY'
import json
from pathlib import Path
for source in sorted(Path('experiments').glob('*.json')):
    request = json.loads(source.read_text())
    for seconds in (6, 40):
        request['budget_seconds'] = seconds
        request['wall_seconds'] = 30 if seconds == 6 else 120
        destination = Path('experiments/requests') / (source.stem + '_' + str(seconds) + '.json')
        destination.write_text(json.dumps(request))
PY
for request in experiments/requests/*.json; do
    name=$(basename "$request" .json)
    seconds=${name##*_}
    output="experiments/states/$name.npz"
    echo "CASE $name"
    if /usr/bin/time -f 'user=%U system=%S wall=%e memory=%M' -o "experiments/timings/$name.txt" bash -c 'ulimit -v 2097152; ulimit -t "$1"; exec python solve.py --request "$2" --output "$3"' _ "$seconds" "$request" "$output"; then
        python contractor.py --request "$request" --state "$output"
    else
        echo FAILED
    fi
    cat "experiments/timings/$name.txt"
done

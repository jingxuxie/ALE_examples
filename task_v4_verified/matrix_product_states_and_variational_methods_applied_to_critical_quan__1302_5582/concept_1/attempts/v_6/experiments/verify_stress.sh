#!/bin/bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python experiments/stress_requests.py
for index in 0 1 2; do
    stem="experiments/stress_${index}"
    (
        ulimit -v 2097152
        ulimit -t 6
        timeout 30 /usr/bin/time -f '%U %S %e %M' -o "${stem}.time" \
            python solve.py --request "${stem}.json" --output "${stem}.npz"
    )
    python contractor.py --request "${stem}.json" --state "${stem}.npz" > "${stem}.measure.json"
done

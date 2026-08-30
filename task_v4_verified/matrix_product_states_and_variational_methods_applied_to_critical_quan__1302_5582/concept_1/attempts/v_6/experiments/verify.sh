#!/bin/bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for name in symmetric odd nonuniform largecritical alternating mixed shallowodd ordered oddcutoff; do
    for budget in 6 40; do
        guard=120
        if [ "$budget" = 6 ]; then guard=30; fi
        stem="experiments/verified_${name}_${budget}"
        (
            ulimit -v 2097152
            ulimit -t "$budget"
            timeout "$guard" /usr/bin/time -f '%U %S %e %M' -o "${stem}.time" \
                python solve.py \
                --request "experiments/${name}_${budget}.json" --output "${stem}.npz"
        )
        python contractor.py --request "experiments/${name}_${budget}.json" \
            --state "${stem}.npz" > "${stem}.measure.json"
        echo "$name $budget"
        cat "${stem}.measure.json" "${stem}.time"
    done
done

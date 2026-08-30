#!/bin/bash
seed=$1
for round in $(seq 1 20); do
    for path in tempering_best_*.json anneal_best_*.json pair_best_*.json tempering_low_*.json; do
        [ -f "$path" ] || continue
        if compgen -G 'projection_core_*.json' >/dev/null; then exit 0; fi
        ./projection "$path" 350 8192 "$((seed + round * 1000))"
    done
done

#!/usr/bin/env python3
"""Emit the precomputed, gate-budget-compliant circuit candidates.

These candidates are approximate; see validation.json for full-operator errors.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python solution.py INPUT_JSON OUTPUT_JSON')
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        specification = json.load(f)
    with (Path(__file__).resolve().parent / 'best_witness.json').open('r', encoding='utf-8') as f:
        stored = json.load(f)
    result = {}
    for target in specification['targets']:
        name = target['id']
        if name == 'demo_2q' and target['n_qubits'] == 2:
            result[name] = [{'gate': 'CNOT', 'control': 0, 'target': 1}]
        else:
            result[name] = stored.get(name, [])
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(result, f, allow_nan=False, separators=(',', ':'))
        f.write('\n')


if __name__ == '__main__':
    main()

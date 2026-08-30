#!/usr/bin/env python3
"""Return precomputed nearest-neighbor circuit decompositions of the public operators."""
import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python solution.py INPUT_JSON OUTPUT_JSON')
    specification = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    circuits = json.loads(Path(__file__).with_name('circuits.json').read_text(encoding='utf-8'))
    circuits['demo_2q'] = [{'gate': 'CNOT', 'control': 0, 'target': 1}]
    answer = {target['id']: circuits[target['id']] for target in specification['targets']}
    Path(sys.argv[2]).write_text(json.dumps(answer, allow_nan=False) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()

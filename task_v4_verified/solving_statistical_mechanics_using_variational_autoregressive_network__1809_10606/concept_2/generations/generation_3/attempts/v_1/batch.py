import argparse
import json
import time
from pathlib import Path

import numpy as np

from compact import optimize as compact_optimize
from exact import EDGES, evaluate
from minimax import minimax
from sectors import best_sector


def canonical(witness):
    lookup = {tuple(sorted(edge)): index for index, edge in enumerate(EDGES)}
    codes = []
    free = witness['order'][12:]
    for swap in [False, True]:
        for row_sign in [-1, 1]:
            for column_sign in [-1, 1]:
                for row_shift in range(4):
                    for column_shift in range(4):
                        permutation = []
                        for site in range(16):
                            row, column = divmod(site, 4)
                            if swap:
                                row, column = column, row
                            permutation.append(4 * ((row_sign * row + row_shift) % 4) + (column_sign * column + column_shift) % 4)
                        code = 0
                        for coupling, (first, second) in zip(witness['bonds'], EDGES):
                            if coupling < 0:
                                code |= 1 << lookup[tuple(sorted([permutation[first], permutation[second]]))]
                        for site in free:
                            code |= 1 << (32 + permutation[site])
                        codes.append(code)
    return min(codes)


def run(source, count, prefix, method, start_index=0):
    records = json.loads(Path(source).read_text())
    seen = set()
    selected = []
    for score, witness, report in records:
        key = canonical(witness)
        if key not in seen:
            seen.add(key)
            selected.append(witness)
    print('unique',len(selected),flush=True)
    best_score = 0.0
    start = time.time()
    for index, witness in enumerate(selected[start_index:start_index + count], start_index):
        if method == 'compact':
            result = compact_optimize(witness, 250)
        else:
            result = minimax(witness, 130, verbose=False)
        result, _, _ = best_sector(result, strict=False)
        report = evaluate(result)
        print(index, round(time.time() - start, 1), report, flush=True)
        Path(f'{prefix}_{index}.json').write_text(json.dumps(result))
        if report['core_score'] > best_score:
            best_score = report['core_score']
            Path(prefix + '_best.json').write_text(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--prefix', default='batch')
    parser.add_argument('--method', default='compact')
    parser.add_argument('--start', type=int, default=0)
    arguments = parser.parse_args()
    run(arguments.source, arguments.count, arguments.prefix, arguments.method, arguments.start)

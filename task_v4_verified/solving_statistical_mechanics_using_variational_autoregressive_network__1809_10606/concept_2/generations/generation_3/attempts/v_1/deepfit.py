import argparse
import json
import time
from pathlib import Path

import numpy as np

from exact import EDGES, STATES, evaluate
from fit import fit_target, make_target
from sectors import best_sector


def transforms():
    lookup = {tuple(sorted(edge)): index for index, edge in enumerate(EDGES)}
    rows = []
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
                        indices = np.zeros(32, dtype=int)
                        for index, (first, second) in enumerate(EDGES):
                            indices[lookup[tuple(sorted([permutation[first], permutation[second]]))]] = index
                        rows.append(indices)
    return np.array(rows)


TRANSFORMS = transforms()


def gauge_key(bonds):
    couplings = np.asarray(bonds)[TRANSFORMS]
    gauge = np.ones((128, 16), dtype=int)
    for site in range(1, 16):
        parent = site - 1 if site % 4 else site - 4
        edge = 2 * parent + int(site % 4 == 0)
        gauge[:, site] = gauge[:, parent] * couplings[:, edge]
    normalized = couplings * gauge[:, [edge[0] for edge in EDGES]] * gauge[:, [edge[1] for edge in EDGES]]
    codes = (normalized < 0) @ (1 << np.arange(32, dtype=np.int64))
    return int(codes.min())


def search(count, prefix, seed, minimum_size=3, maximum_size=1000, minimum_energy=-100):
    random = np.random.default_rng(seed)
    candidates = json.loads(Path('small.json').read_text()) + json.loads(Path('survey.json').read_text())
    candidates = [candidate for candidate in candidates if minimum_size <= len(candidate['cluster']) <= maximum_size
                  and candidate['ground_energy'] >= minimum_energy]
    size_priority = {5: 0, 4: 1, 6: 2, 7: 3, 8: 4, 9: 5, 3: 6}
    candidates.sort(key=lambda candidate: (candidate['ground_energy'] != -20, size_priority.get(len(candidate['cluster']), 10), -candidate['quality']))
    seen = set()
    selected = []
    for candidate in candidates:
        key = gauge_key(candidate['bonds'])
        if key not in seen:
            seen.add(key)
            selected.append(candidate)
        if len(selected) >= count:
            break
    print('distinct',len(selected),flush=True)
    records = []
    start = time.time()
    for index, candidate in enumerate(selected):
        cluster = STATES[candidate['cluster']]
        certainty = ((cluster.T @ cluster / len(cluster)) ** 2).sum(axis=1)
        for trial in range(3):
            teacher_beta = [1.0, 1.5, 2.2][trial]
            order = np.argsort(-(certainty + random.random(16) * .5)).tolist()
            probability = make_target(candidate, teacher_beta, softness=8)
            weights = fit_target(probability, order)
            witness = {'schema_version': 1, 'bonds': candidate['bonds'], 'beta': 1.0,
                       'order': order, 'weights': weights.tolist(), 'pattern': candidate['pattern'],
                       'radius': candidate['radius']}
            witness, _, _ = best_sector(witness, strict=False)
            report = evaluate(witness)
            records.append((report['core_score'], witness, report))
            records.sort(key=lambda record: -record[0])
            Path(prefix + '_records.json').write_text(json.dumps(records))
            Path(prefix + '_best.json').write_text(json.dumps(records[0][1]))
            print(index, len(candidate['cluster']), candidate['ground_energy'], trial,
                  round(time.time() - start, 1), report, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=50)
    parser.add_argument('--prefix', default='deep')
    parser.add_argument('--seed', type=int, default=662)
    parser.add_argument('--minimum-size', type=int, default=3)
    parser.add_argument('--maximum-size', type=int, default=1000)
    parser.add_argument('--minimum-energy', type=float, default=-100)
    arguments = parser.parse_args()
    search(arguments.count, arguments.prefix, arguments.seed, arguments.minimum_size, arguments.maximum_size, arguments.minimum_energy)

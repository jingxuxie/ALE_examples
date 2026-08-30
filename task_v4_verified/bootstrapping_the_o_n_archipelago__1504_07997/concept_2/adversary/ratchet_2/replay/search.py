import itertools
import json
import sys
import time

import numpy as np

from champion_core import INPUT, ROOT, Solver


def search(instance):
    solver = Solver(instance)
    previous = json.loads((ROOT / (instance['id'] + '.json')).read_text())
    support = [atom['index'] for atom in previous['atoms']]
    vectors = np.array([atom['ope'] for atom in previous['atoms']])
    solver.evaluate(support, vectors)
    for sweep in range(6):
        baseline = solver.best_error
        anchor = solver.best
        support = [atom['index'] for atom in anchor['atoms']]
        vectors = np.array([atom['ope'] for atom in anchor['atoms']])
        print('SWEEP', instance['id'], sweep, baseline, flush=True)
        for position in np.argsort(np.sum(vectors ** 2, axis=1)):
            if position == 0:
                continue
            candidates = [index for index in range(solver.design.shape[1]) if index not in support]
            old_column = solver.design[:, support[position]]
            candidates.sort(key=lambda index: np.linalg.norm(solver.design[:, index] - old_column))
            for index in candidates:
                new_support = support.copy()
                new_support[position] = index
                order = np.argsort(new_support)
                new_support = [new_support[offset] for offset in order]
                initial = vectors[order].copy()
                solver.fit(new_support, initial)
                if solver.best_error < 5e-9:
                    return
                solver.tried.discard(tuple(new_support))
                solver.fit(new_support)
                if solver.best_error < 5e-9:
                    return
        if solver.best_error >= baseline * (1 - 1e-6):
            print('STALLED', instance['id'], flush=True)
            return


def main():
    instances = json.loads(INPUT.read_text())['instances']
    for instance in instances:
        if instance['id'] in sys.argv[1:]:
            search(instance)
    cases = [json.loads((ROOT / (instance['id'] + '.json')).read_text()) for instance in instances]
    (ROOT / 'answer.json').write_text(json.dumps({'cases': cases}, indent=2) + '\n')


if __name__ == '__main__':
    main()

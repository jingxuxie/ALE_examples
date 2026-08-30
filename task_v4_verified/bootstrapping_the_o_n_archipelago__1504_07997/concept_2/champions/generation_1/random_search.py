import json
import sys

import numpy as np
from scipy.optimize import nnls

from solve import INPUT, ROOT, Solver


def run(instance):
    solver = Solver(instance)
    saved = json.loads((ROOT / (instance['id'] + '.json')).read_text())
    solver.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
    random = np.random.default_rng(57319)
    candidates = np.array([index for index, candidate in enumerate(instance['candidates']) if index != 0 and candidate['spin'] == 0 and 3.0 < candidate['dimension'] < 4.0])
    for iteration in range(3000):
        anchor = solver.best
        support = [atom['index'] for atom in anchor['atoms']]
        vectors = np.array([atom['ope'] for atom in anchor['atoms']])
        mode = iteration % 4
        if mode == 0:
            vectors[1:] += random.normal(size=vectors[1:].shape) * 0.4
        elif mode == 1:
            for position in random.choice(np.arange(1, len(support)), size=2, replace=False):
                available = np.array([index for index in candidates if index not in support])
                support[position] = int(random.choice(available))
            order = np.argsort(support)
            support = [support[position] for position in order]
            vectors = vectors[order]
        else:
            support = [0] + sorted(int(index) for index in random.choice(candidates, size=solver.limit-1, replace=False))
            vectors = random.normal(size=(solver.limit, 2)) * 0.4
            vectors[0] = np.array(anchor['atoms'][0]['ope'])
        solver.fit(support, vectors)
        if iteration % 50 == 0:
            print('ITERATION', iteration, solver.best_error, flush=True)
        if solver.best_error < 2e-9:
            return


if __name__ == '__main__':
    for instance in json.loads(INPUT.read_text())['instances']:
        if instance['id'] in sys.argv[1:]:
            run(instance)

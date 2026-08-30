import heapq
import itertools
import json
import sys

import numpy as np

from solve import INPUT, ROOT, Solver


def enumerate_case(instance):
    solver = Solver(instance)
    saved = json.loads((ROOT / (instance['id'] + '.json')).read_text())
    solver.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
    fixed = [0]
    if instance['family'] == 'weak_residues':
        fixed += [atom['index'] for atom in saved['atoms'] if instance['candidates'][atom['index']]['spin'] != 0]
        candidates = [index for index, candidate in enumerate(instance['candidates']) if index not in fixed and candidate['spin'] == 0]
    else:
        candidates = list(range(1, 24))
    combinations = itertools.combinations(candidates, instance['max_atoms'] - len(fixed))
    best = []
    count = 0
    while True:
        batch = list(itertools.islice(combinations, 1024))
        if not batch:
            break
        supports = np.array([sorted(fixed + list(indices)) for indices in batch])
        matrices = solver.design[:, supports].transpose(1, 0, 2)
        left, singular, right = np.linalg.svd(matrices, full_matrices=False)
        projected = np.einsum('brk,rc->bkc', left, solver.target) / singular[:, :, None]
        coefficients = np.einsum('bkj,bkc->bjc', right, projected)
        traces = coefficients[:, :, 0] + coefficients[:, :, 2]
        gaps = np.sqrt((coefficients[:, :, 0] - coefficients[:, :, 2]) ** 2 + 4 * coefficients[:, :, 1] ** 2)
        lower = (traces - gaps) / 2
        upper = (traces + gaps) / 2
        losses = np.sum(lower ** 2 + np.minimum(upper, 0) ** 2, axis=1)
        losses += (coefficients[:, 0, 0] - solver.shared) ** 2
        for offset in np.argsort(losses)[:100]:
            record = (-float(losses[offset]), tuple(int(index) for index in supports[offset]))
            if len(best) < 300:
                heapq.heappush(best, record)
            elif record > best[0]:
                heapq.heapreplace(best, record)
        count += len(batch)
        if count % 10240 == 0:
            print('ENUMERATED', count, 'loss', -max(best)[0], max(best)[1], flush=True)
    ranked = sorted([(-loss, support) for loss, support in best])
    (ROOT / (instance['id'] + '_ranked_supports.json')).write_text(json.dumps(ranked))
    for position, (loss, support) in enumerate(ranked):
        print('CANDIDATE', position, loss, support, flush=True)
        solver.fit(support)
        if solver.best_error < 1e-9:
            break


if __name__ == '__main__':
    instances = json.loads(INPUT.read_text())['instances']
    for instance in instances:
        if instance['id'] in sys.argv[1:]:
            enumerate_case(instance)

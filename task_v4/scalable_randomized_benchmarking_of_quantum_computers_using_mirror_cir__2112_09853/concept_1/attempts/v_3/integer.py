import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import itertools
import json
import time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
import search


def create_moves(family):
    moves = [np.zeros(192, dtype=np.int16)]
    layer_range = range(24) if family == 0 else range(24, 32)
    for first_layer, second_layer in itertools.combinations(layer_range, 2):
        common = sorted(set(search.model.SUPPORTS[first_layer]) & set(search.model.SUPPORTS[second_layer]))
        for first_label, second_label in itertools.combinations(common, 2):
            move = np.zeros(192, dtype=np.int16)
            move[search.MAPPING[first_layer, first_label]] = 1
            move[search.MAPPING[first_layer, second_label]] = -1
            move[search.MAPPING[second_layer, first_label]] = -1
            move[search.MAPPING[second_layer, second_label]] = 1
            moves.extend([move, -move])
    matrix = np.array(moves)
    sparse = csr_matrix(matrix)
    cross = (sparse[:, search.PAIR] @ sparse.T).toarray()
    return matrix, cross


MOVES = [create_moves(family) for family in (0, 1)]


def repair(counts, family, target, limit=80, optimize=False):
    matrix, cross = MOVES[family]
    feasible = np.all((counts + matrix >= search.LOWER) & (counts + matrix <= search.UPPER), axis=1)
    indices = np.flatnonzero(feasible)
    selected = matrix[indices]
    current_overlap = int(search.overlaps(counts)[family])
    change = 2 * (selected @ (counts - search.BASE)[search.PAIR]) + np.diag(cross)[indices]
    total_overlap = current_overlap + change[:, None] + change[None, :] + 2 * cross[np.ix_(indices, indices)]
    firsts, seconds = np.where(total_overlap == 0)
    keep = firsts <= seconds
    firsts, seconds = firsts[keep], seconds[keep]
    if not len(firsts):
        return None
    gradient = search.metrics(counts, True)[2]
    score_change = selected @ gradient
    predicted = score_change[firsts] + score_change[seconds]
    if optimize:
        keep = predicted > -1e-8
        firsts, seconds, predicted = firsts[keep], seconds[keep], predicted[keep]
    order = np.argsort(-predicted)
    best = None
    best_score = -np.inf
    checked = 0
    for candidate in order:
        updated = counts + selected[firsts[candidate]] + selected[seconds[candidate]]
        if np.any(updated < search.LOWER) or np.any(updated > search.UPPER):
            continue
        measured = search.metrics(updated)[0]
        if measured[0] > best_score:
            best, best_score = updated, measured[0]
        checked += 1
        if checked >= limit:
            break
    return best


def save(counts, name):
    artifact = search.artifact(counts)
    search.model.check_constraints(artifact)
    measured, signal, gradient = search.metrics(counts)
    previous = -1
    incumbent = search.ROOT / 'witness.json'
    if incumbent.exists():
        previous_rows = search.model.rows_of(json.loads(incumbent.read_text()))
        previous = search.metrics(np.concatenate(previous_rows))[0][0]
    if measured[0] > previous:
        incumbent.write_text(json.dumps(artifact, indent=2) + '\n')
        (search.ROOT / f'{name}.json').write_text(json.dumps(artifact, indent=2) + '\n')
        print('NEW BEST', name, measured, 'tail', signal[-1], flush=True)
    return measured[0]


def nearest(target, seed):
    rng = np.random.default_rng(seed)
    lower = np.maximum(search.LOWER, np.floor(target + 1e-6))
    upper = np.minimum(search.UPPER, np.ceil(target - 1e-6))
    cost = 2 * lower + 1 - 2 * target
    if seed:
        cost += rng.normal(size=192) * 0.6
    result = linprog(cost, A_eq=search.LINEAR, b_eq=search.LINEAR @ search.BASE,
                     bounds=np.stack((lower, upper), axis=1), method='highs')
    if not result.success:
        print('LP failure', result.message, flush=True)
        return None
    counts = np.rint(result.x)
    assert np.max(np.abs(search.LINEAR @ (counts - search.BASE))) == 0
    return counts


def refine(counts, name, iterations=40):
    current_score = search.metrics(counts)[0][0]
    for iteration in range(iterations):
        improved = False
        for family in (0, 1):
            candidate = repair(counts, family, counts, limit=30, optimize=True)
            if candidate is None:
                continue
            candidate_score = search.metrics(candidate)[0][0]
            if candidate_score > current_score + 1e-11:
                counts = candidate
                current_score = candidate_score
                improved = True
                save(counts, f'{name}_refined')
        if not improved:
            break
    return counts


if __name__ == '__main__':
    candidates = []
    for path in search.ROOT.glob('continuous_*.npy'):
        target = np.load(path)
        if np.max(np.abs(search.overlaps(target))) < 1e-4:
            candidates.append((search.metrics(target)[0][0], path))
    candidates.sort(reverse=True)
    print('candidates', [(score, path.name) for score, path in candidates], flush=True)
    for score, path in candidates[:12]:
        target = np.load(path)
        for seed in range(10):
            counts = nearest(target, seed)
            if counts is None:
                continue
            print('rounded', path.name, seed, search.metrics(counts)[0][0], search.overlaps(counts), flush=True)
            for family in (0, 1):
                counts = repair(counts, family, target)
                if counts is None:
                    print('repair failed', family, flush=True)
                    break
            if counts is not None:
                save(counts, f'integer_{path.stem}_{seed}')
                refine(counts, f'integer_{path.stem}_{seed}')
    print('finished', flush=True)

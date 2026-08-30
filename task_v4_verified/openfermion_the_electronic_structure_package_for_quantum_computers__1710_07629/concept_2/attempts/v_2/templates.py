import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from optimize import fit, parameters_gates
from synthesize import load_instances, projector, rotate, schedule


def colorings(instance):
    edges = [tuple(edge) for edge in instance['edges']]
    size = instance['n_modes']
    incident = [[] for mode in range(size)]
    for index, edge in enumerate(edges):
        for mode in edge:
            incident[mode].append(index)
    colors = [-1] * len(edges)
    used = [set() for mode in range(size)]

    def visit(remaining, largest):
        if not remaining:
            yield [[edge for edge, color in zip(edges, colors) if color == choice] for choice in range(3)]
            return
        index = max(remaining, key=lambda index: len(used[edges[index][0]] | used[edges[index][1]]))
        first, second = edges[index]
        for choice in range(min(2, largest + 1) + 1):
            if choice in used[first] or choice in used[second]:
                continue
            colors[index] = choice
            used[first].add(choice)
            used[second].add(choice)
            yield from visit(remaining - {index}, max(largest, choice))
            used[first].remove(choice)
            used[second].remove(choice)
            colors[index] = -1

    yield from visit(set(range(len(edges))), -1)


def sample(instance, matchings, order):
    size = instance['n_modes']
    diagonal = np.zeros(size)
    diagonal[instance['initial_occupied']] = 1
    matrix = np.diag(diagonal).astype(complex)
    generator = np.random.default_rng(17)
    edges = []
    for matching_index in order:
        for first, second in matchings[matching_index]:
            if abs(matrix[first, first] - matrix[second, second]) < 1e-13 and (abs(matrix[first, first]) < 1e-13 or abs(matrix[first, first] - 1) < 1e-13):
                continue
            edges.append((first, second))
            matrix = rotate(matrix, first, second, generator.uniform(0.2, 1.0), generator.uniform(-3, 3))
    return edges, matrix


def rank_profile(matrix, subsets):
    size = len(matrix)
    ranks = []
    for subset in subsets:
        other = [mode for mode in range(size) if mode not in subset]
        singular = np.linalg.svd(matrix[np.ix_(subset, other)], compute_uv=False)
        ranks.append(np.count_nonzero(singular > 1e-9))
    return np.array(ranks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', required=True)
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--layers', type=int, default=6)
    arguments = parser.parse_args()
    instance = next(instance for instance in load_instances() if instance['id'] == arguments.instance)
    target = projector(instance)
    support = abs(target) > 1e-10
    subsets = [tuple(edge) for edge in instance['edges']]
    subsets += list(itertools.combinations(range(instance['n_modes']), 3))
    target_ranks = rank_profile(target, subsets)
    ranked = []
    counter = 0
    for matching_index, matchings in enumerate(colorings(instance)):
        for order in itertools.permutations(range(3)):
            order = (order * ((arguments.layers + 2) // 3))[:arguments.layers]
            edges, matrix = sample(instance, matchings, order)
            difference = np.count_nonzero((abs(matrix) > 1e-10) != support)
            ranked.append((difference, edges, matrix, matching_index, order))
        counter += 1
    ranked.sort(key=lambda entry: entry[0])
    print(instance['id'], 'colorings', counter, 'best supports', [(entry[0], entry[3], entry[4], len(entry[1])) for entry in ranked[:20]], flush=True)
    cutoff = ranked[min(len(ranked) - 1, 100)][0]
    selected = []
    for difference, edges, matrix, matching_index, order in ranked:
        if difference > cutoff:
            continue
        rank_difference = np.sum(np.abs(rank_profile(matrix, subsets) - target_ranks))
        selected.append((int(difference + 2 * rank_difference), edges, matching_index, order))
    selected.sort(key=lambda entry: entry[0])
    print('RANKED', [(entry[0], entry[2], entry[3], len(entry[1])) for entry in selected[:30]], flush=True)
    Path(instance['id'] + '_templates.json').write_text(json.dumps([dict(score=entry[0], edges=entry[1], coloring=entry[2], order=entry[3]) for entry in selected]))
    started = time.time()
    for index, (score, edges, matching_index, order) in enumerate(selected[:arguments.limit]):
        parameters, error, evaluations = fit(instance, edges, max_evaluations=500)
        print('FIT', instance['id'], 'template', index, 'score', score, 'error', error,
              'evaluations', evaluations, 'elapsed', round(time.time() - started, 1), flush=True)
        if error < 1e-8:
            gates = parameters_gates(edges, parameters)
            circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
            Path(instance['id'] + '_template_solution.json').write_text(json.dumps(circuit))
            print('SOLVED', instance['id'], 'gates', len(gates), 'depth', len(circuit['layers']), flush=True)
            break


if __name__ == '__main__':
    main()

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import Problem, optimize, project
from verify import BOUND, EDGES, LOWER, evaluate


ROOT = Path(__file__).resolve().parent
FREE = [4, 6, 13, 15]
CORE = [site for site in range(16) if site not in FREE]
CORE_EDGES = [(int(first), int(second)) for first, second in EDGES if first in CORE and second in CORE]


def candidates(base):
    bonds = base['bonds']
    free_couplings = np.zeros((4, 16))
    for edge, (first, second) in enumerate(EDGES):
        if first in FREE:
            free_couplings[FREE.index(first), second] = bonds[edge]
        if second in FREE:
            free_couplings[FREE.index(second), first] = bonds[edge]
    candidates_list = []
    for indices in itertools.combinations(range(len(CORE_EDGES)), 11):
        neighbors = {site: [] for site in CORE}
        for index in indices:
            first, second = CORE_EDGES[index]
            neighbors[first].append(second)
            neighbors[second].append(first)
        root = 5
        parent = {root: None}
        order = [root]
        for site in order:
            for neighbor in neighbors[site]:
                if neighbor not in parent:
                    order.append(neighbor)
                    parent[neighbor] = site
        if len(order) != 12:
            continue
        descendants = {site: {site} for site in CORE}
        for site in order[:0:-1]:
            descendants[parent[site]].update(descendants[site])
        costs = []
        for site in order[1:]:
            flipped = descendants[site]
            cut = sum((first in flipped) != (second in flipped) for first, second in CORE_EDGES)
            spins = np.ones(16)
            spins[list(flipped)] = -1
            fields = free_couplings @ spins
            cost = 2 * cut - np.log(np.cosh(fields)).sum()
            costs.append(cost)
        proxy = np.sum(np.maximum(np.array(costs) - BOUND, 0) ** 2 * .01)
        candidates_list.append((proxy, -min(costs), indices, order, parent, costs))
    candidates_list.sort(key=lambda item: item[:3])
    print('trees', len(candidates_list), 'best proxies', [(round(item[0], 5), round(-item[1], 5), np.round(item[5], 3).tolist()) for item in candidates_list[:10]], flush=True)
    return candidates_list, free_couplings


def make_witness(base, item, free_couplings, strategy):
    proxy, negative_minimum, indices, core_order, parents, costs = item
    witness = json.loads(json.dumps(base))
    order = core_order + FREE
    inverse = np.argsort(order)
    weights = np.zeros((16, 16))
    for site, cost in zip(core_order[1:], costs):
        if strategy == 'saturated':
            cost = BOUND
        weights[inverse[site], inverse[parents[site]]] = min(max(cost, 0), BOUND - 1e-10)
    for free_index, site in enumerate(FREE):
        weights[inverse[site], :12] = free_couplings[free_index, core_order] * (BOUND - 1e-10) / 4
    witness['order'] = order
    witness['weights'] = weights.tolist()
    return witness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--screen', type=int, default=300)
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--iterations', type=int, default=250)
    parser.add_argument('--strategy', default='cavity')
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    items, free_couplings = candidates(base)
    screened = []
    for index, item in enumerate(items[:arguments.screen]):
        witness = make_witness(base, item, free_couplings, arguments.strategy)
        problem = Problem(witness)
        metrics, derivatives = problem.calculate(np.array(witness['weights'])[LOWER])
        merit = metrics[1]
        screened.append((merit, index, witness))
    screened.sort(key=lambda item: item[0])
    print('screened', [(round(item[0], 5), item[1]) for item in screened[:30]], flush=True)
    for merit, index, witness in screened[:arguments.count]:
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'tree_{arguments.strategy}_{index}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', index, report['core_score'], report['metrics'], flush=True)
        if report['core_score'] > .15:
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=300, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'tree_{arguments.strategy}_{index}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', index, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

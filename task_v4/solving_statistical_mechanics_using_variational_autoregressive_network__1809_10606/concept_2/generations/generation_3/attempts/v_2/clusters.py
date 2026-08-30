import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import Problem, optimize
from verify import BOUND, EDGES, LOWER, evaluate


ROOT = Path(__file__).resolve().parent
FREE = [4, 6, 13, 15]
CENTERS = [5, 7, 12, 14]
LEAVES = [0, 1, 2, 3, 8, 9, 10, 11]
CORE = CENTERS + LEAVES


def candidates(base):
    bonds = base['bonds']
    free_couplings = np.zeros((4, 16))
    core_edges = []
    for edge, (first, second) in enumerate(EDGES):
        if first in FREE:
            free_couplings[FREE.index(first), second] = bonds[edge]
        elif second in FREE:
            free_couplings[FREE.index(second), first] = bonds[edge]
        else:
            core_edges.append((first, second, bonds[edge]))
    costs = {}
    for center in CENTERS:
        for first, second in itertools.combinations(LEAVES, 2):
            flipped = {center, first, second}
            cut = sum(coupling for first_site, second_site, coupling in core_edges
                      if (first_site in flipped) != (second_site in flipped))
            spins = np.ones(16)
            spins[list(flipped)] = -1
            fields = free_couplings @ spins
            costs[center, first, second] = 2 * cut - np.log(np.cosh(fields)).sum()
    variants = []
    index = 0
    for first_pair in itertools.combinations(LEAVES, 2):
        remaining = [site for site in LEAVES if site not in first_pair]
        for second_pair in itertools.combinations(remaining, 2):
            last_four = [site for site in remaining if site not in second_pair]
            for third_pair in itertools.combinations(last_four, 2):
                fourth_pair = tuple(site for site in last_four if site not in third_pair)
                pairs = [first_pair, second_pair, third_pair, fourth_pair]
                index += 1
                cluster_costs = [costs[(center, pair[0], pair[1])] for center, pair in zip(CENTERS, pairs)]
                for root_index in range(4):
                    cost_values = [cost for center_index, cost in enumerate(cluster_costs) if center_index != root_index]
                    merit = np.sum((np.array(cost_values) - BOUND) ** 2)
                    variants.append((merit, index, root_index, pairs, cost_values))
    variants.sort(key=lambda item: item[:3])
    print('best cuts', [(round(item[0], 6), item[1], item[2], np.round(item[4], 4).tolist()) for item in variants[:20]], flush=True)
    return variants, free_couplings


def make_witness(base, variant, free_couplings):
    merit, index, root_index, pairs, costs = variant
    root = CENTERS[root_index]
    order = [root] + [site for site in CENTERS if site != root] + LEAVES + FREE
    inverse = np.argsort(order)
    weights = np.zeros((16, 16))
    for center, pair in zip(CENTERS, pairs):
        if center != root:
            weights[inverse[center], 0] = BOUND - 1e-10
        for site in pair:
            weights[inverse[site], inverse[center]] = BOUND - 1e-10
    for free_index, site in enumerate(FREE):
        weights[inverse[site], :12] = free_couplings[free_index, order[:12]] * (BOUND - 1e-10) / 4
    witness = json.loads(json.dumps(base))
    witness['order'] = order
    witness['weights'] = weights.tolist()
    return witness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--screen', type=int, default=240)
    parser.add_argument('--count', type=int, default=12)
    parser.add_argument('--iterations', type=int, default=240)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    variants, free_couplings = candidates(base)
    screened = []
    for variant in variants[:arguments.screen]:
        witness = make_witness(base, variant, free_couplings)
        problem = Problem(witness)
        metrics, derivatives = problem.calculate(np.array(witness['weights'])[LOWER])
        screened.append((metrics[1], variant[1], variant[2], witness))
    screened.sort(key=lambda item: item[:3])
    print('screened', [(round(item[0], 7), item[1], item[2]) for item in screened[:30]], flush=True)
    for merit, index, root_index, witness in screened[:arguments.count]:
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'cluster_{index}_{root_index}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', index, root_index, report['core_score'], report['metrics'], flush=True)
        if report['metrics']['reward_variance'] < .25:
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=300, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'cluster_{index}_{root_index}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', index, root_index, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

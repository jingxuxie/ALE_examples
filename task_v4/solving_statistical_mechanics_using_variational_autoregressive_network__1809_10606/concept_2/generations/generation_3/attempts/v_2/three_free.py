import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import Problem, optimize
from verify import BOUND, EDGES, LOWER, PRODUCTS, evaluate, frustrated


ROOT = Path(__file__).resolve().parent
FREE = [4, 6, 13]
CORE = [site for site in range(16) if site not in FREE]


def candidates(base):
    incidence = [np.flatnonzero(np.any(EDGES == site, axis=1)) for site in FREE]
    counts = {site: sum(np.any(EDGES[indices] == site) for indices in incidence) for site in CORE}
    isolated = [site for site in CORE if counts[site] == 0]
    internal = [index for index, (first, second) in enumerate(EDGES) if first in isolated and second in isolated]
    variants = []
    index = 0
    for negative_edge, choices, low_value in itertools.product(internal, itertools.product(range(1, 4), repeat=3), [1.35, BOUND - 1e-10]):
        index += 1
        witness = json.loads(json.dumps(base))
        bonds = np.ones(32, dtype=int)
        bonds[negative_edge] = -1
        for indices, choice in zip(incidence, choices):
            bonds[indices[0]] = -1
            bonds[indices[choice]] = -1
        if not 4 <= frustrated(bonds) <= 12:
            continue
        energy = -PRODUCTS @ bonds
        if energy.min() != -18:
            continue
        root = next(site for site in isolated if site not in EDGES[negative_edge])
        main = [site for site in CORE if site != root and counts[site] < 2]
        low = [site for site in CORE if counts[site] == 2]
        order = [root] + main + low + FREE
        inverse = np.argsort(order)
        weights = np.zeros((16, 16))
        for site in main:
            weights[inverse[site], 0] = 4 if counts[site] == 0 else BOUND - 1e-10
        for site in low:
            weights[inverse[site], 0] = low_value
        for site, indices in zip(FREE, incidence):
            for edge in indices:
                neighbor = EDGES[edge, int(EDGES[edge, 0] == site)]
                weights[inverse[site], inverse[neighbor]] = bonds[edge] * (BOUND - 1e-10) / 4
        witness['bonds'] = bonds.tolist()
        witness['order'] = order
        witness['weights'] = weights.tolist()
        problem = Problem(witness)
        metrics, derivatives = problem.calculate(weights[LOWER])
        variants.append((metrics[1], index, witness))
    variants.sort(key=lambda item: item[0])
    print('screened', [(round(item[0], 6), item[1]) for item in variants], flush=True)
    return variants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=220)
    parser.add_argument('--offset', type=int, default=0)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    variants = candidates(base)
    for merit, index, witness in variants[arguments.offset:arguments.offset + arguments.count]:
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'three_{index}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', index, report['core_score'], report['metrics'], flush=True)
        if report['metrics']['reward_variance'] < .25:
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=300, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'three_{index}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', index, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

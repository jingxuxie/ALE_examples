import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import Problem, optimize
from verify import BOUND, EDGES, LOWER, PRODUCTS, evaluate, frustrated


ROOT = Path(__file__).resolve().parent


def candidates(base):
    free = [4, 6, 13, 15]
    incident = [np.flatnonzero(np.any(EDGES == site, axis=1)) for site in free]
    options = [list(itertools.combinations(list(indices)[1:], 1)) for indices in incident]
    generated = []
    for index, choices in enumerate(itertools.product(*options)):
        witness = json.loads(json.dumps(base))
        bonds = np.ones(32, dtype=int)
        for indices, extra in zip(incident, choices):
            bonds[indices[0]] = -1
            bonds[list(extra)] = -1
        if not 4 <= frustrated(bonds) <= 12:
            continue
        energy = -PRODUCTS @ bonds
        if energy.min() < -16:
            continue
        witness['bonds'] = bonds.tolist()
        matrix = np.array(witness['weights'])
        order = witness['order']
        inverse = np.argsort(order)
        for site, indices in zip(free, incident):
            row = inverse[site]
            matrix[row] = 0
            for edge in indices:
                neighbor = EDGES[edge, int(EDGES[edge, 0] == site)]
                matrix[row, inverse[neighbor]] = bonds[edge] * (BOUND - 1e-10) / 4
        witness['weights'] = matrix.tolist()
        problem = Problem(witness)
        metrics, derivatives = problem.calculate(matrix[LOWER])
        merit = max(metrics[1] / .05, np.max(np.abs(derivatives[0])) / .003)
        signature = tuple(np.bincount((energy.astype(int) + 32) // 4, minlength=17))
        generated.append((merit, index, signature, witness))
    generated.sort(key=lambda item: item[0])
    return generated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--count', type=int, default=15)
    parser.add_argument('--iterations', type=int, default=200)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    generated = candidates(base)
    print('Candidates', [(round(item[0], 5), item[1], item[2][4]) for item in generated], flush=True)
    seen = set()
    selected = []
    for item in generated:
        if item[2] not in seen:
            selected.append(item)
            seen.add(item[2])
    selected.extend(item for item in generated if item[1] not in [chosen[1] for chosen in selected])
    for merit, index, signature, witness in selected[:arguments.count]:
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'bond_{index}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', index, report['core_score'], report['metrics'], flush=True)
        if report['core_score'] > .15:
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=300, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'bond_{index}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', index, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

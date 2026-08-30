import argparse
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import optimize
from verify import EDGES, PRODUCTS, evaluate, frustrated


ROOT = Path(__file__).resolve().parent


def matchings():
    result = []

    def recurse(remaining, chosen):
        if not remaining:
            bonds = np.ones(32, dtype=int)
            bonds[chosen] = -1
            frustration = frustrated(bonds)
            if 4 <= frustration <= 12:
                energy = -PRODUCTS @ bonds
                if energy.min() == -16:
                    result.append((frustration, bonds.tolist()))
            return
        first = min(remaining)
        for edge, (endpoint, other) in enumerate(EDGES):
            if first == endpoint and other in remaining:
                recurse(remaining - {endpoint, other}, chosen + [edge])
            elif first == other and endpoint in remaining:
                recurse(remaining - {endpoint, other}, chosen + [edge])

    recurse(set(range(16)), [])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--orders', type=int, default=4)
    parser.add_argument('--iterations', type=int, default=250)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    seen = set()
    for frustration, bonds in matchings():
        if frustration in seen:
            continue
        seen.add(frustration)
        for seed in range(arguments.orders):
            witness = json.loads(json.dumps(base))
            witness['bonds'] = bonds
            witness['beta'] = 1.
            rng = np.random.default_rng(seed)
            witness['order'] = [int(site) for site in rng.permutation(16)]
            weights = np.zeros((16, 16))
            weights[1:, 0] = 4.
            witness['weights'] = weights.tolist()
            witness, sector = best_sector(witness)
            print('initial', frustration, seed, evaluate(witness)['metrics'], flush=True)
            witness, result = optimize(witness, objective='variance', constraints=False,
                                       iterations=arguments.iterations, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'matching_{frustration}_{seed}.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('variance', frustration, seed, report['core_score'], report['metrics'], flush=True)
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=400, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'matching_{frustration}_{seed}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', frustration, seed, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

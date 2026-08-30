import argparse
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from refine import refine
from search import Problem, optimize, project
from verify import LOWER, evaluate


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'global_dp_76_2_minimax.json')
    parser.add_argument('--count', type=int, default=6)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    for seed in range(arguments.count):
        witness = json.loads(json.dumps(base))
        if seed < 2:
            temperatures = ([.85, .9, .95, 1.] if seed == 0 else [.7, .8, .9, 1.])
            for beta in temperatures:
                witness['beta'] = beta
                witness, result = optimize(witness, objective='variance', constraints=False,
                                           iterations=170, verbosity=0)
                problem = Problem(witness)
                metrics, derivatives = problem.calculate(np.array(witness['weights'])[LOWER])
                print('stage', seed, beta, metrics, flush=True)
        else:
            rng = np.random.default_rng(seed)
            weights = np.array(witness['weights'])
            values = weights[LOWER]
            values += rng.normal(0, [.005, .02, .05, .12][(seed - 2) % 4], 120)
            weights[LOWER] = project(values)
            witness['weights'] = weights.tolist()
            witness, result = optimize(witness, objective='variance', constraints=False,
                                       iterations=250, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=350, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = refine(witness, iterations=150, verbose=False)
        witness, sector = best_sector(witness)
        filename = ROOT / f'continuation_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('final', seed, evaluate(witness), flush=True)


if __name__ == '__main__':
    main()

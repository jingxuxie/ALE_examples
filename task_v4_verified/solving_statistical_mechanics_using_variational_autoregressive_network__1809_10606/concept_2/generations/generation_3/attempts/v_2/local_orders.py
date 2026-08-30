import argparse
import json
from pathlib import Path

import numpy as np

from construct import fit_distribution
from landscape import best_sector
from refine import refine
from search import optimize
from verify import evaluate


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'global49_refined.json')
    parser.add_argument('--count', type=int, default=5)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    report, target, distribution, energy, gradients = evaluate(base, True)
    candidates = []
    for position in range(12):
        witness = json.loads(json.dumps(base))
        order = base['order'].copy()
        order[position], order[position + 1] = order[position + 1], order[position]
        witness['order'] = order
        witness['weights'] = fit_distribution(distribution, order).tolist()
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        print('screen', position, report['core_score'], report['metrics'], flush=True)
        candidates.append((report['metrics']['reward_variance'], position, witness))
    candidates.sort(key=lambda item: item[:2])
    for variance, position, witness in candidates[:arguments.count]:
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=220, verbosity=0)
        witness, sector = best_sector(witness)
        witness, result = refine(witness, iterations=200, verbose=False)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'local_order_{position}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('refined', position, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()

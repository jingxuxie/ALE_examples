import argparse
import json
import time
from pathlib import Path

import numpy as np

from construct import fit_distribution
from landscape import best_sector
from search import optimize
from verify import evaluate


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'backbone3_minimax.json')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--count', type=int, default=50)
    parser.add_argument('--all-sites', action='store_true')
    parser.add_argument('--iterations', type=int, default=140)
    arguments = parser.parse_args()
    rng = np.random.default_rng(arguments.seed)
    current = json.loads(arguments.input.read_text())
    current_report = evaluate(current)
    best, best_report = current, current_report
    archive = [(current, current_report)]
    seen = {tuple(current['order'])}
    started = time.time()
    for iteration in range(arguments.count):
        if iteration % 8 == 7:
            current, current_report = archive[int(rng.integers(min(len(archive), 5)))]
        proposal = json.loads(json.dumps(current))
        size = 16 if arguments.all_sites else 12
        while True:
            order = current['order'].copy()
            first, second = rng.choice(size, 2, replace=False)
            if rng.random() < .5:
                order[first], order[second] = order[second], order[first]
            else:
                value = order.pop(first)
                order.insert(second, value)
            if tuple(order) not in seen:
                break
        seen.add(tuple(order))
        report, target, distribution, energy, gradients = evaluate(current, True)
        proposal['order'] = order
        proposal['weights'] = fit_distribution(distribution, order, iterations=100).tolist()
        proposal, result = optimize(proposal, objective='variance', constraints=False,
                                    iterations=arguments.iterations, verbosity=0)
        proposal, sector = best_sector(proposal)
        report = evaluate(proposal)
        if report['metrics']['reward_variance'] < .05 / best_report['core_score'] * 1.2:
            proposal, result = optimize(proposal, objective='minimax', constraints=False,
                                        iterations=arguments.iterations, verbosity=0)
            proposal, sector = best_sector(proposal)
            report = evaluate(proposal)
        score = report['core_score']
        print(iteration, 'seconds', round(time.time() - started), 'score', score,
              'order', order, 'metrics', report['metrics'], flush=True)
        if score > best_report['core_score']:
            best, best_report = proposal, report
            (ROOT / f'evolve_{arguments.seed}_best.json').write_text(json.dumps(best, indent=2) + '\n')
            print('BEST', iteration, score, flush=True)
        archive.append((proposal, report))
        archive.sort(key=lambda item: item[1]['core_score'], reverse=True)
        archive = archive[:10]
        loss_difference = 1 / max(score, 1e-8) - 1 / max(current_report['core_score'], 1e-8)
        if loss_difference <= 0 or rng.random() < np.exp(-loss_difference / .08):
            current, current_report = proposal, report
    print('FINAL', best_report, flush=True)


if __name__ == '__main__':
    main()

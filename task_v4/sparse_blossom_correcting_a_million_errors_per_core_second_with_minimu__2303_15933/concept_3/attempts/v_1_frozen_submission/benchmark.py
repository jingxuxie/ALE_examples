import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np

from solution import Model, solve, design


def main():
    global solve
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='../../participant/input/training.json')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--pilot', type=int, default=100)
    parser.add_argument('--intermediate', type=int, default=12000)
    parser.add_argument('--criterion', default='rms')
    parser.add_argument('--early', type=int, default=0)
    parser.add_argument('--strategy', default='stages')
    parser.add_argument('--episodes', default='0,1,2,3,4,5')
    parser.add_argument('--output', default='benchmark.json')
    parser.add_argument('--random-rates', action='store_true')
    parser.add_argument('--oracle', action='store_true')
    args = parser.parse_args()
    if args.strategy == 'sequential':
        from sequential import solve
    episodes = json.loads(Path(args.input).read_text())['episodes']
    results = []
    cells = {}
    for repeat in range(args.repeat):
        for index in map(int, args.episodes.split(',')):
            episode = episodes[index]
            spec = episode['spec']
            model = Model(spec)
            rates = np.array(episode['rates'])
            rng = np.random.default_rng(episode['sample_seed'] + repeat * 100003)
            if args.random_rates:
                rates = np.exp(rng.uniform(model.bounds[:, 0], model.bounds[:, 1]))
            probability = model.distribution(np.log(rates))
            probability /= probability.sum(axis=1, keepdims=True)
            diagnostics = {}

            def query(action, shots):
                return rng.multinomial(shots, probability[action])

            start = time.process_time()
            if args.oracle:
                allocation, information = design(model, np.log(rates), np.zeros(len(spec['actions'])),
                                                 spec['shot_budget'], args.criterion)
                inverse = np.linalg.inv(np.einsum('a,akl->kl', allocation * spec['shot_budget'], information))
                error = inverse.diagonal()
                diagnostics['used'] = np.round(allocation * spec['shot_budget']).astype(int).tolist()
            else:
                estimates = solve(spec, query, args.pilot, args.intermediate, args.criterion, diagnostics, args.early)
                error = np.log(estimates / rates) ** 2
                diagnostics['estimates'] = estimates.tolist()
                diagnostics['rates'] = rates.tolist()
            elapsed = time.process_time() - start
            scores = {}
            for family in ['boundary', 'bulk', 'hook', 'rare']:
                selected = np.array([channel['family'] == family for channel in spec['channels']])
                scores[family] = float(np.sqrt(error[selected].mean()))
                cells.setdefault((spec['regime'], family), []).extend(error[selected].tolist())
            result = dict(episode=index, repeat=repeat, cpu=elapsed, scores=scores, **diagnostics)
            results.append(result)
            print(json.dumps(result), flush=True)
            Path(args.output).write_text(json.dumps(results, indent=2))
    summary = {str(cell): float(np.sqrt(np.mean(values))) for cell, values in cells.items()}
    print(json.dumps(dict(cells=summary, mean=float(np.mean(list(summary.values()))),
                         worst=max(summary.values()), max_cpu=max(result['cpu'] for result in results)), indent=2))


if __name__ == '__main__':
    main()

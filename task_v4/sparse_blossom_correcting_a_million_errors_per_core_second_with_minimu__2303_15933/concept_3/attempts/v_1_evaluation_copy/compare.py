import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np

from solution import Model, solve
from posterior import posterior_mean


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeat', type=int, default=4)
    parser.add_argument('--pilot', type=int, default=50)
    parser.add_argument('--intermediate', type=int, default=8000)
    parser.add_argument('--criterion', default='trace')
    parser.add_argument('--early', type=int, default=0)
    parser.add_argument('--power', type=int, default=10)
    parser.add_argument('--random-rates', action='store_true')
    parser.add_argument('--output', default='compare.json')
    args = parser.parse_args()
    episodes = json.loads(Path('../../participant/input/training.json').read_text())['episodes']
    results = []
    for repeat in range(args.repeat):
        for index, episode in enumerate(episodes):
            spec = episode['spec']
            model = Model(spec)
            rates = np.array(episode['rates'])
            rng = np.random.default_rng(episode['sample_seed'] + repeat * 100003)
            if args.random_rates:
                rates = np.exp(rng.uniform(model.bounds[:, 0], model.bounds[:, 1]))
            probability = model.distribution(np.log(rates))
            probability /= probability.sum(axis=1, keepdims=True)
            counts = np.zeros_like(probability, dtype=int)
            diagnostics = {}

            def query(action, shots):
                observed = rng.multinomial(shots, probability[action])
                counts[action] += observed
                return observed

            start = time.process_time()
            estimates = solve(spec, query, args.pilot, args.intermediate, args.criterion, diagnostics, args.early)
            after_ml = time.process_time()
            posterior, ess = posterior_mean(model, counts, np.log(estimates), args.power)
            after_bayes = time.process_time()
            error_ml = np.log(estimates / rates) ** 2
            error_bayes = (posterior - np.log(rates)) ** 2
            result = dict(episode=index, repeat=repeat, regime=spec['regime'],
                          cpu_ml=after_ml-start, cpu_bayes=after_bayes-after_ml,
                          ess=ess, error_ml=error_ml.tolist(), error_bayes=error_bayes.tolist(),
                          rates=rates.tolist(), estimates=estimates.tolist(), posterior=posterior.tolist(),
                          families=[channel['family'] for channel in spec['channels']], **diagnostics)
            results.append(result)
            print(index, repeat, 'cpu', round(after_bayes-start, 3), 'ess', round(ess),
                  'ML', np.sqrt(model.family_weights @ error_ml).round(4).tolist(),
                  'Bayes', np.sqrt(model.family_weights @ error_bayes).round(4).tolist(), flush=True)
            Path(args.output).write_text(json.dumps(results))
    for method in ['ml', 'bayes']:
        cells = {}
        for result in results:
            for family, error in zip(result['families'], result['error_' + method]):
                cells.setdefault((result['regime'], family), []).append(error)
        scores = {str(cell): float(np.sqrt(np.mean(values))) for cell, values in cells.items()}
        print(method, json.dumps(dict(cells=scores, mean=float(np.mean(list(scores.values()))),
                                      worst=max(scores.values())), indent=2))


if __name__ == '__main__':
    main()

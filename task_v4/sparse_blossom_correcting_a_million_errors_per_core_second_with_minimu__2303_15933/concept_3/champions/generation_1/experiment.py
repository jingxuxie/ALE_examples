import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import time
from pathlib import Path
import numpy as np
from experimental import Model, calibrate, design, posterior_mean, posterior_integral

parser = argparse.ArgumentParser()
parser.add_argument('--input', default=str(Path(__file__).resolve().parents[2] / 'participant/input/training.json'))
parser.add_argument('--repeats', type=int, default=1)
parser.add_argument('--offset', type=int, default=0)
parser.add_argument('--episode', type=int, default=-1)
parser.add_argument('--oracle', action='store_true')
parser.add_argument('--posterior', action='store_true')
parser.add_argument('--skew', action='store_true')
parser.add_argument('--importance', action='store_true')
parser.add_argument('--random-rates', action='store_true')
parser.add_argument('--strategy', default='v1')
parser.add_argument('--output', default='experiment_results.json')
args = parser.parse_args()
episodes = json.load(open(args.input))['episodes']
records = []
for repeat in range(args.offset, args.offset + args.repeats):
    for episode_id, episode in enumerate(episodes):
        if args.episode >= 0 and episode_id != args.episode:
            continue
        spec = episode['spec']
        truth = np.array(episode['rates'])
        model = Model(spec)
        if args.random_rates:
            rate_rng = np.random.default_rng(189328 + episode_id * 5791 + repeat * 357293)
            truth = np.exp(rate_rng.uniform(model.bounds[:, 0], model.bounds[:, 1]))
        probabilities = model.distribution(np.log(truth))
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        rng = np.random.default_rng(episode['sample_seed'] + repeat * 125789)
        allocations = np.zeros(len(spec['actions']), dtype=int)
        if args.oracle:
            for criterion in ('root', 'a'):
                fractions = design(model, np.log(truth), allocations, 40000, criterion)
                covariance = np.linalg.inv(np.einsum('a,akl->kl', 40000 * fractions, model.fisher(np.log(truth))))
                risks = np.sqrt(model.groups @ np.diag(covariance))
                print(episode_id, criterion, 'risk', risks.round(4).tolist(), 'mean', round(risks.mean(), 4), flush=True)
                print('allocation', (fractions * 40000).astype(int).tolist(), flush=True)
            continue
        def query(action, shots):
            allocations[action] += shots
            return rng.multinomial(shots, probabilities[action])
        started = time.process_time()
        model, counts, fitted = calibrate(spec, query, debug=True, return_state=True, strategy=args.strategy)
        estimated = np.exp(fitted)
        cpu = time.process_time() - started
        errors = np.log(estimated / truth)
        risks = np.sqrt(model.groups @ errors ** 2)
        record = {'episode': episode_id, 'regime': spec['regime'], 'repeat': repeat,
                  'cpu': cpu, 'errors': errors.tolist(), 'risks': risks.tolist(),
                  'allocations': allocations.tolist()}
        if args.posterior or args.importance:
            posterior = posterior_mean(model, counts, fitted, skew=args.skew)
            if args.importance:
                laplace_errors = posterior - np.log(truth)
                record['laplace_errors'] = laplace_errors.tolist()
                record['laplace_risks'] = np.sqrt(model.groups @ laplace_errors ** 2).tolist()
                posterior, diagnostic = posterior_integral(model, counts, fitted, details=True)
                record['posterior_diagnostic'] = diagnostic
            posterior_errors = posterior - np.log(truth)
            record['posterior_errors'] = posterior_errors.tolist()
            record['posterior_risks'] = np.sqrt(model.groups @ posterior_errors ** 2).tolist()
        cpu = time.process_time() - started
        record['cpu'] = cpu
        if model.quadrature_diagnostics:
            record['moment_diagnostics'] = model.quadrature_diagnostics
        records.append(record)
        print(episode_id, repeat, 'cpu', round(cpu, 2), 'risk', risks.round(4).tolist(), 'mean', round(risks.mean(), 4), flush=True)
        Path(args.output).write_text(json.dumps(records, indent=2))
if records:
    cells = []
    for regime in sorted(set(record['regime'] for record in records)):
        risks = np.array([record['risks'] for record in records if record['regime'] == regime])
        pooled = np.sqrt(np.mean(risks ** 2, axis=0))
        cells.extend(pooled)
        print(regime, pooled.round(5).tolist(), flush=True)
    print('MEAN', np.mean(cells), 'WORST', np.max(cells), flush=True)

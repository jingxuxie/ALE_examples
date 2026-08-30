import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import sys
import time
import resource
from pathlib import Path
import numpy as np
import importlib
solution = importlib.import_module(os.environ.get('SOLUTION_MODULE', 'solution'))

parser = argparse.ArgumentParser()
parser.add_argument('--episode', type=int, default=5)
parser.add_argument('--seed', type=int)
parser.add_argument('--random-rates', action='store_true')
parser.add_argument('--output', default='experiment.json')
parser.add_argument('--refine', type=int, default=0)
args = parser.parse_args()
source = Path(os.environ['P']) / 'input'
sys.path.insert(0, str(source))
from simulator import sample_events
episode = json.loads((source / 'training.json').read_text())['episodes'][args.episode]
spec = episode['spec']
truth = np.array(episode['rates'])
seed = episode['sample_seed'] if args.seed is None else args.seed
rng = np.random.default_rng(seed)
if args.random_rates:
    bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
    truth = np.exp(rng.uniform(bounds[:, 0], bounds[:, 1]))
families = np.array([channel['family'] for channel in spec['channels']])
def scores(rates):
    errors = np.log(rates / truth) ** 2
    return {family: float(np.sqrt(np.mean(errors[families == family]))) for family in sorted(set(families))}
transcript = []
def query(action, shots):
    syndromes, multiplicities = sample_events(spec, truth, action, shots, rng)
    transcript.append({'action': action, 'shots': shots, 'syndromes': syndromes.tolist(), 'multiplicities': multiplicities.tolist()})
    return syndromes, multiplicities
original_fit = solution.Model.fit
checkpoints = []
def wrapped_fit(model, *positional, **keywords):
    fitted = original_fit(model, *positional, **keywords)
    score = scores(np.exp(fitted))
    print('score', score, file=sys.stderr, flush=True)
    checkpoints.append({'cpu': time.process_time(), 'scores': score})
    if args.refine and model.spent.sum() == spec['shot_budget'] and keywords.get('width') == 12:
        fitted = original_fit(model, fitted, width=args.refine, hashbits=16, maxiter=40, deadline=120)
        print('refined', scores(np.exp(fitted)), file=sys.stderr, flush=True)
    return fitted
solution.Model.fit = wrapped_fit
started = time.process_time()
estimated = solution.calibrate(spec, query)
result = {'episode': args.episode, 'seed': seed, 'scores': scores(estimated), 'cpu': time.process_time()-started,
          'rss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'rates': estimated.tolist(), 'truth': truth.tolist(),
          'transcript': transcript, 'checkpoints': checkpoints}
Path(args.output).write_text(json.dumps(result))
print(json.dumps({key: value for key, value in result.items() if key not in ('rates', 'truth', 'transcript', 'checkpoints')}, indent=2))

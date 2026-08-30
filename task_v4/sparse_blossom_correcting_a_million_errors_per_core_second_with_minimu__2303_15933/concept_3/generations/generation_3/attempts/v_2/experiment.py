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
import solution

parser = argparse.ArgumentParser()
parser.add_argument('--episode', type=int, default=0)
parser.add_argument('--seed', type=int)
parser.add_argument('--random-rates', action='store_true')
parser.add_argument('--output')
parser.add_argument('--record')
parser.add_argument('--limit', action='store_true')
args = parser.parse_args()
if args.limit:
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (59, 60))
participant = Path(os.environ['PART'])
sys.path.insert(0, str(participant / 'input'))
from simulator import sample_events
episode = json.loads((participant / 'input/training.json').read_text())['episodes'][args.episode]
spec = episode['spec']
rates = np.array(episode['rates'])
seed = args.seed if args.seed is not None else episode['sample_seed']
rng = np.random.default_rng(seed)
if args.random_rates:
    bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
    rates = np.exp(rng.uniform(bounds[:, 0], bounds[:, 1]))
shots_used = 0
queries = 0
sample_cpu = 0
observations = []

def query(action, shots):
    global shots_used, queries, sample_cpu
    start = time.process_time()
    shots_used += shots
    queries += 1
    assert shots_used <= 40000 and queries <= 64 and shots <= 4000
    result = sample_events(spec, rates, action, shots, rng)
    observations.append((action, result[0].tolist(), result[1].tolist()))
    sample_cpu += time.process_time() - start
    return result

start = time.process_time()
estimated = solution.calibrate(spec, query)
elapsed = time.process_time() - start - sample_cpu
families = np.array([channel['family'] for channel in spec['channels']])
errors = np.log(estimated / rates)
scores = {family: float(np.sqrt(np.mean(errors[families == family]**2))) for family in sorted(set(families))}
report = {'episode': args.episode, 'seed': seed, 'random': args.random_rates, 'scores': scores,
          'cpu': elapsed, 'shots': shots_used, 'queries': queries,
          'total_cpu': time.process_time(), 'limits_enabled': args.limit,
          'rss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'rates': rates.tolist(), 'estimated': estimated.tolist()}
print(json.dumps({key: value for key, value in report.items() if key not in ('rates', 'estimated')}, indent=2))
if args.output:
    Path(args.output).write_text(json.dumps(report, indent=2))
if args.record:
    Path(args.record).write_text(json.dumps({'episode': args.episode, 'rates': rates.tolist(),
                                          'estimated': estimated.tolist(), 'observations': observations}))

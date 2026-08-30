import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import importlib.util
import json
import sys
sys.dont_write_bytecode = True
import time
import resource
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
if not (ROOT / 'solution.py').is_file():
    ROOT = ROOT.parent

parser = argparse.ArgumentParser()
parser.add_argument('--episode', type=int, default=0)
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--random-rates', action='store_true')
parser.add_argument('--solution', default=str(ROOT / 'solution.py'))
parser.add_argument('--output', default='experiment.json')
parser.add_argument('--save-data', action='store_true')
parser.add_argument('--extend', action='store_true')
parser.add_argument('--corner', choices=['lower', 'upper'])
parser.add_argument('--limit', action='store_true')
args = parser.parse_args()
participant = Path(os.environ['P'])
sys.path.insert(0, str(participant / 'input'))
from simulator import sample_events
entry = json.loads((participant / 'input/training.json').read_text())['episodes'][args.episode]
spec = entry['spec']
rates = np.array(entry['rates'])
rng = np.random.default_rng(481519 + args.seed * 31251 + args.episode * 197)
if args.limit:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
if args.extend:
    import copy
    assert spec['detector_count'] == 18
    spec = copy.deepcopy(spec)
    spec['detector_count'] = 20
    edges = [(18, 16), (18, 17), (18, 19), (19, 17), (19, 15)]
    spec['detector_edges'] += edges
    additions = [('boundary', [1 << detector] * 2) for detector in (18, 19)]
    additions += [('bulk', [(1 << first) | (1 << second)] * 2) for first, second in edges]
    additions += [('hook', [(1 << 16) | (1 << 17) | (1 << 18), (1 << 17) | (1 << 18) | (1 << 19)])]
    original = list(spec['channels'])
    for index, (family, masks) in enumerate(additions):
        candidates = [channel for channel, data in enumerate(original) if data['family'] == family]
        source = candidates[(7 * index + args.seed) % len(candidates)]
        data = copy.deepcopy(original[source])
        data['id'] = 'extension_' + str(index)
        data['masks'] = masks
        spec['channels'].append(data)
        rates = np.append(rates, np.sqrt(np.prod(data['rate_bounds'])))
        for action in spec['actions']:
            action['exposures'][0].append(action['exposures'][0][source])
            action['exposures'][1].append(action['exposures'][1][source])
            action['alternate_probability'].append(action['alternate_probability'][source])
if args.random_rates:
    bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
    rates = np.exp(rng.uniform(bounds[:, 0], bounds[:, 1]))
if args.corner:
    rates = np.array([channel['rate_bounds'][int(args.corner == 'upper')] for channel in spec['channels']])
module_spec = importlib.util.spec_from_file_location('submission', args.solution)
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
original_fit = module.Model.fit
last_fit = []

def record_fit(model, *arguments, **keywords):
    point = original_fit(model, *arguments, **keywords)
    last_fit[:] = [model, point]
    return point

module.Model.fit = record_fit
allocations = []

def query(action, shots):
    allocations.append((action, shots))
    return sample_events(spec, rates, action, shots, rng)

estimated = module.calibrate(spec, query)
errors = np.log(estimated / rates)
families = np.array([channel['family'] for channel in spec['channels']])
scores = {family: float(np.sqrt(np.mean(errors[families == family] ** 2))) for family in sorted(set(families))}
report = dict(episode=args.episode, seed=args.seed, random_rates=args.random_rates, cpu=time.process_time(),
              scores=scores, rates=rates.tolist(), estimates=estimated.tolist(), allocations=allocations)
report['maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
assert sum(shots for action, shots in allocations) <= spec['shot_budget']
assert len(allocations) <= spec['max_queries']
assert all(0 <= action < len(spec['actions']) and 0 < shots <= spec['max_shots_per_query'] for action, shots in allocations)
report['mle'] = np.exp(last_fit[1]).tolist()
if args.save_data:
    np.savez_compressed(str(Path(args.output).with_suffix('.npz')), counts=last_fit[0].raw_counts,
                        spent=last_fit[0].spent, fitted=last_fit[1], rates=rates)
Path(args.output).write_text(json.dumps(report))
print(args.output, scores, 'cpu', report['cpu'], flush=True)

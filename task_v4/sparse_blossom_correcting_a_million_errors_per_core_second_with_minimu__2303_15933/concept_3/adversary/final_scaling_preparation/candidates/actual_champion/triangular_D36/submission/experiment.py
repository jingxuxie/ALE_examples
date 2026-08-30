import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import sys
import time
import numpy as np
import solution

sys.path.insert(0, str(solution.Path(__file__).resolve().parents[2] / 'participant' / 'input'))
from simulator import sample_events

episode_id = int(sys.argv[1])
seed_offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
path = solution.Path(__file__).resolve().parents[2] / 'participant' / 'input' / 'training.json'
episode = json.loads(path.read_text())['episodes'][episode_id]
spec = episode['spec']
if len(sys.argv) > 3 and sys.argv[3] != 'extend':
    spec['detector_count'] = int(sys.argv[3])
rates = np.array(episode['rates'])
if seed_offset >= 10000:
    generator = np.random.default_rng(seed_offset)
    bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
    rates = np.exp(generator.uniform(bounds[:, 0], bounds[:, 1]))
if len(sys.argv) > 3 and sys.argv[3] == 'extend':
    generator = np.random.default_rng(7231 + seed_offset)
    spec['detector_count'] = 20
    spec['detector_edges'].extend([[13, 18], [8, 18], [13, 19], [18, 19]])
    additions = [('boundary', [18], [18]), ('boundary', [19], [19]),
                 ('bulk', [13, 18], [8, 18]), ('bulk', [8, 18], [13, 18]),
                 ('bulk', [13, 19], [18, 19]), ('bulk', [18, 19], [13, 19]),
                 ('hook', [8, 13, 18], [13, 18, 19]), ('hook', [13, 18, 19], [8, 13, 18])]
    original_count = len(spec['channels'])
    for family, primary, alternate in additions:
        candidates = [index for index, channel in enumerate(spec['channels'][:original_count]) if channel['family'] == family]
        source = int(generator.choice(candidates))
        channel = dict(spec['channels'][source])
        channel['id'] = 'extension_' + str(len(spec['channels']))
        channel['masks'] = [sum(1 << detector for detector in footprint) for footprint in (primary, alternate)]
        spec['channels'].append(channel)
        for action in spec['actions']:
            action['exposures'][0].append(action['exposures'][0][source])
            action['exposures'][1].append(action['exposures'][1][source])
            action['alternate_probability'].append(action['alternate_probability'][source])
        rates = np.append(rates, np.exp(generator.uniform(*np.log(channel['rate_bounds']))))
if len(sys.argv) > 4:
    fraction = float(sys.argv[4])
    bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
    rates = np.exp(bounds[:, 0] + fraction * (bounds[:, 1] - bounds[:, 0]))
rng = np.random.default_rng(episode['sample_seed'] + seed_offset)
allocations = np.zeros(len(spec['actions']), dtype=int)
queries = 0
snapshots = []
original_fit = solution.Model.fit

def tracked_fit(self, *args, **kwargs):
    fitted = original_fit(self, *args, **kwargs)
    error = fitted - np.log(rates)
    scores = np.sqrt(self.groups @ (error ** 2))
    snapshots.append({'shots': int(self.spent.sum()), 'states': self.states, 'cpu': time.process_time(),
                      'scores': scores.tolist(), 'logrates': fitted.tolist()})
    print('fit', self.spent.sum(), self.states, scores.round(4), file=sys.stderr)
    return fitted

solution.Model.fit = tracked_fit

def query(action, shots):
    global queries
    allocations[action] += shots
    queries += 1
    assert queries <= spec['max_queries'] and shots <= spec['max_shots_per_query']
    assert allocations.sum() <= spec['shot_budget']
    return sample_events(spec, rates, action, shots, rng)

estimates = solution.calibrate(spec, query)
error = np.log(estimates / rates)
scores = {family: float(np.sqrt(np.mean(error[[channel['family'] == family for channel in spec['channels']]] ** 2)))
          for family in ('boundary', 'bulk', 'hook', 'rare')}
print(json.dumps({'episode': episode_id, 'seed_offset': seed_offset, 'scores': scores, 'cpu': time.process_time(),
                  'allocations': allocations.tolist(), 'queries': queries, 'errors': error.tolist(), 'snapshots': snapshots}))

import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import json
from pathlib import Path
import time
import numpy as np
from experimental import Model, calibrate, posterior_integral

episodes = json.load(open('../../participant/input/training.json'))['episodes']
records = []
for episode_id in (0, 2, 4):
    spec = episodes[episode_id]['spec']
    model = Model(spec)
    for case in ('lower', 'upper', 'mixed', 'rare_lower', 'rare_upper'):
        truth = model.bounds.mean(axis=1)
        if case in ('lower', 'upper'):
            truth = model.bounds[:, int(case == 'upper')]
        elif case == 'mixed':
            truth = model.bounds[np.arange(len(truth)), np.arange(len(truth)) % 2]
        else:
            truth[-4:] = model.bounds[-4:, int(case == 'rare_upper')]
        probability = model.distribution(truth)
        probability /= probability.sum(axis=1, keepdims=True)
        rng = np.random.default_rng(67214 + episode_id)
        totals = [0, 0]
        def query(action, shots):
            assert 1 <= shots <= 4000
            totals[0] += shots
            totals[1] += 1
            assert totals[0] <= 40000 and totals[1] <= 64
            return rng.multinomial(shots, probability[action])
        started = time.process_time()
        model, counts, fitted = calibrate(spec, query, strategy='posterior', return_state=True)
        estimate, diagnostic = posterior_integral(model, counts, fitted, details=True)
        assert np.all(np.isfinite(estimate))
        record = {'episode': episode_id, 'case': case, 'cpu': time.process_time() - started,
                  'queries': totals[1], 'ess': diagnostic['ess'],
                  'risk': np.sqrt(model.groups @ (estimate - truth) ** 2).tolist()}
        records.append(record)
        print(record, flush=True)
        Path('stress_results.json').write_text(json.dumps(records, indent=2))

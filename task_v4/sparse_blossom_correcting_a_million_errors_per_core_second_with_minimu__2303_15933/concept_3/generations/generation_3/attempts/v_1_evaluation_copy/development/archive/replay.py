import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
import importlib
solution = importlib.import_module(os.environ.get('SOLUTION_MODULE', 'solution'))

record = json.loads(Path(sys.argv[1]).read_text())
episode = json.loads((Path(os.environ['P']) / 'input/training.json').read_text())['episodes'][record['episode']]
model = solution.Model(episode['spec'])
truth = np.array(record['truth'])
for observation in record['transcript']:
    action = observation['action']
    model.raw[action].append((np.array(observation['syndromes'], dtype=np.int64), np.array(observation['multiplicities'])))
    model.spent[action] += observation['shots']
point = np.log(record['rates'])
def score(point):
    error = (point - np.log(truth)) ** 2
    return dict(zip(('boundary', 'bulk', 'hook', 'rare'), np.sqrt(model.groups @ error)))
print('initial', score(point), flush=True)
for width in map(int, sys.argv[2:]):
    if width == 0:
        import posterior
        point = posterior.apply(model, point)
    elif width < 0:
        import refine
        point, center, covariance = refine.refine(model, point, width=-width)
    else:
        point = model.fit(point, width=width, hashbits=16, maxiter=45, deadline=300)
    print('width', width, 'cpu', time.process_time(), score(point), flush=True)

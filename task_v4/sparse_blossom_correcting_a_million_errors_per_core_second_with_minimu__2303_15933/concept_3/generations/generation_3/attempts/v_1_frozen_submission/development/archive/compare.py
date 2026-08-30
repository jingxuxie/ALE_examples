import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import sys
import time
from pathlib import Path
import numpy as np
import policy_v3
import conditional
import posterior

record = json.loads(Path(sys.argv[1]).read_text())
spec = json.loads((Path(os.environ['P']) / 'input/training.json').read_text())['episodes'][record['episode']]['spec']
truth = np.array(record['truth'])
results = {}
for name, model_type, width in [('marginal12', policy_v3.Model, 12), ('marginal14', policy_v3.Model, 14), ('conditional14', conditional.Model, 14)]:
    model = model_type(spec)
    for observation in record['transcript']:
        action = observation['action']
        model.raw[action].append((np.array(observation['syndromes'], dtype=np.int64), np.array(observation['multiplicities'])))
        model.spent[action] += observation['shots']
    point = np.log(record['rates'])
    started = time.process_time()
    if width != 12:
        point = model.fit(point, width=width, hashbits=16, maxiter=45, deadline=300)
    for post in [False, True]:
        if post:
            point = posterior.apply(model, point, width=width, hashbits=15 if width == 12 else 16)
        errors = (point - np.log(truth)) ** 2
        key = name + ('post' if post else '')
        results[key] = {'scores': dict(zip(('boundary', 'bulk', 'hook', 'rare'), np.sqrt(model.groups @ errors))),
                        'rates': np.exp(point).tolist(), 'cpu': time.process_time()-started}
        print(key, results[key]['scores'], flush=True)
Path(sys.argv[2]).write_text(json.dumps(results))

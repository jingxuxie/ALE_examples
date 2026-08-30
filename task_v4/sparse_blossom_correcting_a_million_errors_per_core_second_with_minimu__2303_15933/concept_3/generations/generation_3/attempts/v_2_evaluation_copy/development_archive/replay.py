import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import sys
import time
from pathlib import Path
import numpy as np
import solution

record = json.loads(Path(sys.argv[1]).read_text())
spec = json.loads((Path(os.environ['PART']) / 'input/training.json').read_text())['episodes'][record['episode']]['spec']
model = solution.Model(spec, bits=int(sys.argv[2]))
for action, syndromes, counts in record['observations']:
    syndromes = np.array(syndromes, dtype=np.int64)
    counts = np.array(counts)
    model.raw[action].append((syndromes, counts))
    model.spent[action] += counts.sum()
point = model.fit(np.log(record['estimated']), deadline=55, joint=bool(os.environ.get('JOINT')))
families = np.array([channel['family'] for channel in spec['channels']])
errors = point - np.log(record['rates'])
scores = {family: float(np.sqrt(np.mean(errors[families == family]**2))) for family in sorted(set(families))}
result = {'scores': scores, 'estimated': np.exp(point).tolist(), 'cpu': time.process_time()}
print(json.dumps({'blocks': len(model.blocks), 'scores': scores, 'cpu': time.process_time()}))
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps(result))

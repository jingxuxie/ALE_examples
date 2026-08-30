import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np

from fast_physics import SmallRing


if __name__ == '__main__':
    paths = ('../../participant/input/train.jsonl', '../../participant/input/validation.jsonl',
             'independent_1.jsonl', 'independent_2.jsonl')
    records = [json.loads(line) for path in paths for line in Path(path).read_text().splitlines()]
    records = [record for record in records if record['L'] == 10]
    ring = SmallRing()
    with ThreadPoolExecutor(4) as executor:
        predictions = list(executor.map(ring.predict, [record['fields'] for record in records]))
    errors = np.array(predictions) - np.array([record['f'] for record in records])
    symmetry_errors = []
    for family in sorted({record['family'] for record in records}):
        selected = sorted([record for record in records if record['family'] == family],
                          key=lambda record: record['f'])
        for record in (selected[0], selected[len(selected) // 2], selected[-1]):
            fields = np.array(record['fields'])
            expected = ring.predict(fields)
            for transformed in (fields + 2.4, -fields, fields[::-1], np.roll(fields, 3)):
                symmetry_errors.append(abs(ring.predict(transformed) - expected))
    metrics = {'records': len(records), 'rmse': float(np.sqrt(np.mean(errors ** 2))),
               'maximum_absolute_error': float(np.max(np.abs(errors))),
               'maximum_symmetry_error': max(symmetry_errors)}
    assert metrics['rmse'] < 0.0001
    assert metrics['maximum_absolute_error'] < 0.001
    assert metrics['maximum_symmetry_error'] < 0.001
    Path('physics_report.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps(metrics))

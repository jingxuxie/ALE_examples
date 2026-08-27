import csv
import json
import math
from pathlib import Path
import numpy as np


def read_output(directory):
    with (Path(directory) / 'trajectory.csv').open() as handle:
        rows = [{column: float(value) for column, value in row.items()} for row in csv.DictReader(handle)]
    stats = json.loads((Path(directory) / 'stats.json').read_text())
    return {'rows': rows, 'initial_energy': float(stats['initial_energy']), 'stats': stats}


def error_metric(case, measured, expected):
    rows, targets = measured['rows'], expected['rows']
    if len(rows) != len(targets) or any(abs(row['time'] - target['time']) > 1e-8 for row, target in zip(rows, targets)):
        raise ValueError('Incorrect sampling grid')
    scales = {'charge': max(1, len(case['region'])), 'number': case['n_sites'], 'spin': case['n_sites'] / 2,
              'phonon': max(1, len(case['phonons'])), 'current': 1, 'source': 1, 'energy': case['n_sites']}
    errors = {}
    for name, scale in scales.items():
        values = [(row[name] - target[name]) / scale for row, target in zip(rows, targets)]
        errors[name] = float(np.sqrt(np.mean(np.square(values))))
    errors['initial_energy'] = abs(measured['initial_energy'] - expected['initial_energy']) / case['n_sites']
    if not all(math.isfinite(value) for value in errors.values()):
        raise ValueError('Non-finite physical output')
    if any(not 0.8 < row['norm'] < 1.2 for row in rows):
        raise ValueError('Invalid propagated norm')
    aggregate = 0.5 * max(errors.values()) + 0.5 * float(np.sqrt(np.mean(np.square(list(errors.values())))))
    return aggregate, errors


def quality(error, weak, strong):
    weak = max(weak, 0.03)
    strong = min(max(strong, 1e-7), weak / 100)
    return float(np.clip(np.log(weak / max(error, 1e-12)) / np.log(weak / strong), 0, 1))

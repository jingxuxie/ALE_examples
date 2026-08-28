import csv
import json
import os
from pathlib import Path
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
names = ['impurity_dev_production', 'ladder_dev_baseline', 'paired_dev_final_tensor',
         'spin_orbit_dev_final_tensor', 'vibronic_dev_production', 'mixed_nonlocal_odd_tensor160',
         'impurity_dev_legacy_clock_U']
checks = []
for name in names:
    original = ROOT / 'runs' / name
    output = ROOT / 'replays' / name
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'run.log').open('w') as handle:
        subprocess.run(['bash', str(original / 'replay.sh'), str(output)], check=True,
                       stdout=handle, stderr=subprocess.STDOUT, timeout=175)
    values = []
    for directory in (original, output):
        values.append(np.array([[float(row[column]) for column in
                                 ['norm', 'charge', 'number', 'spin', 'phonon', 'current', 'source', 'energy']]
                                for row in csv.DictReader((directory / 'trajectory.csv').open())]))
    first = json.loads((original / 'stats.json').read_text())
    second = json.loads((output / 'stats.json').read_text())
    difference = float(np.max(abs(values[0] - values[1])))
    checks.append(dict(row_id=name, maximum_replay_difference=difference,
                       initial_energy_difference=abs(first['initial_energy'] - second['initial_energy'])))
    assert difference < 1e-6, checks[-1]
with (ROOT / 'replay_checks.csv').open('w') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
    writer.writeheader()
    writer.writerows(checks)
print(json.dumps(checks, indent=2))

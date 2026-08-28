import csv
import json
import math

from experiments import ROOT, run


case = dict(id='onsite_pair_analytic', n_sites=1, sector=dict(kind='parity', value=0),
            onsite=dict(before=[0], after=[0]), interaction=[0], zeeman=[0], edges=[],
            pairing=[dict(sites=[0, 0], spins=[0, 1], before=[1, 0], after=[0, 1])],
            density_edges=[], phonons=[], region=[0], layout=[0], times=[0, 0.1, 0.2, 0.5])
run(case, case['id'] + '_production')
directory = ROOT / 'runs' / (case['id'] + '_production')
rows = list(csv.DictReader((directory / 'trajectory.csv').open()))
errors = []
for row in rows:
    instant = float(row['time'])
    errors.extend([abs(float(row['number']) - (1 - math.sin(2 * instant))),
                   abs(float(row['source']) + 2 * math.cos(2 * instant)), abs(float(row['current']))])
error = max(errors)
assert error < 1e-12, error
(ROOT / 'analytic_checks.json').write_text(json.dumps(dict(
    onsite_pair_max_error=error, expected_initial_energy=-1,
    measured_initial_energy=json.loads((directory / 'stats.json').read_text())['initial_energy'],
    formulas=dict(number='1-sin(2t)', source='-2*cos(2t)', current='0')), indent=2))
print('Analytic onsite-pair check:', error)

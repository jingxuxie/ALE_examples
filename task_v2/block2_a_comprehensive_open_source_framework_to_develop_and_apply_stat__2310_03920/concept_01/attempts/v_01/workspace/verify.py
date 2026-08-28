import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

from sparse_solver import build


ROOT = Path(__file__).resolve().parents[1]
checks = []
for name in ['impurity', 'ladder', 'spin_orbit', 'paired']:
    directory = ROOT / 'runs' / (name + '_dev_production')
    case = json.loads((directory / 'case.json').read_text())
    stats = json.loads((directory / 'stats.json').read_text())
    rows = list(csv.DictReader((directory / 'trajectory.csv').open()))
    matrices, diagonals = build(case)
    initial_eigenvalues, initial_vectors = eigh(matrices['before'].toarray(), subset_by_index=[0, 0])
    final_eigenvalues, final_vectors = eigh(matrices['after'].toarray())
    coefficients = final_vectors.conj().T @ initial_vectors[:, 0]
    errors = []
    for row in rows:
        state = final_vectors @ (np.exp(-1j * float(row['time']) * final_eigenvalues) * coefficients)
        probabilities = abs(state) ** 2
        for column, diagonal in diagonals.items():
            errors.append(abs(float(probabilities @ diagonal) - float(row[column])))
        for column, operator in [('energy', matrices['after']), ('current', matrices['current']), ('source', matrices['source'])]:
            errors.append(abs(float(np.vdot(state, operator @ state).real) - float(row[column])))
    check = dict(row_id=name + '_dense_spectral', case=case['id'], dimension=matrices['before'].shape[0],
                 initial_energy_error=abs(float(initial_eigenvalues[0]) - stats['initial_energy']),
                 max_observable_error=float(max(errors)))
    checks.append(check)
    assert check['initial_energy_error'] < 1e-9 and check['max_observable_error'] < 1e-9, check
with (ROOT / 'spectral_checks.csv').open('w') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
    writer.writeheader()
    writer.writerows(checks)
for table in ['results.csv', 'ablation.csv', 'scaling.csv']:
    rows = list(csv.DictReader((ROOT / table).open()))
    assert len({row['row_id'] for row in rows}) == len(rows), table
    if table == 'ablation.csv':
        for row in rows:
            for column in ['left_run', 'right_run']:
                assert (ROOT / 'runs' / row[column] / 'stats.json').exists()
    if table == 'scaling.csv':
        for row in rows:
            assert float(row['peak_rss_mb']) < 4096, row
            directory = ROOT / 'runs' / row['row_id']
            assert (directory / 'case.json').exists() and (directory / 'profile.txt').exists()
    if table == 'results.csv':
        for row in rows:
            assert all(math.isfinite(float(row[column])) for column in
                       ['time', 'norm', 'charge', 'current', 'source', 'number', 'spin', 'phonon', 'energy'])
            assert float(row['norm']) > 0
summary = dict(spectral_checks=checks, table_identifiers_unique=True, run_references_present=True,
               all_successful_runs_below_4096_mb=True, all_observables_finite=True)
if (ROOT / 'replay_checks.csv').exists():
    replay_rows = list(csv.DictReader((ROOT / 'replay_checks.csv').open()))
    summary['selected_fresh_replays'] = len(replay_rows)
    summary['maximum_fresh_replay_difference'] = max(float(row['maximum_replay_difference']) for row in replay_rows)
(ROOT / 'verification.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))

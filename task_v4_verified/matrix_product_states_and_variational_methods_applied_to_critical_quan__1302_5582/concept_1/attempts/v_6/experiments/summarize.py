import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contractor import load_mps, measure


names = ['symmetric', 'odd', 'nonuniform', 'largecritical', 'alternating',
         'mixed', 'shallowodd', 'ordered', 'oddcutoff']
records = []
for name in names:
    for budget in (6, 40):
        request = json.loads(Path(f'experiments/{name}_{budget}.json').read_text())
        stem = Path(f'experiments/verified_{name}_{budget}')
        result = json.loads(Path(f'{stem}.measure.json').read_text())
        state_path = Path(f'{stem}.npz')
        if state_path.exists():
            recomputed = measure(load_mps(state_path, request), request)
            assert abs(recomputed['energy'] - result['energy']) < 1e-10
        user, system, wall, rss = map(float, Path(f'{stem}.time').read_text().split())
        assert user + system < budget
        assert wall < (30 if budget == 6 else 120)
        baseline_path = Path(f'experiments/baseline_{name}_{budget}.measure.json')
        if baseline_path.exists():
            baseline = json.loads(baseline_path.read_text())
        else:
            baseline = measure(load_mps(f'experiments/baseline_{name}_{budget}.npz', request), request)
            baseline_path.write_text(json.dumps(baseline, indent=2) + '\n')
        records.append(dict(case=name, public_example=name in names[:3],
                            n_sites=request['n_sites'], local_dim=request['local_dim'],
                            bond_cap=request['bond_cap'], sector=request['sector'],
                            budget_seconds=budget, valid=True, **result,
                            cpu_seconds=user + system, wall_seconds=wall,
                            max_rss_kib=int(rss), baseline_energy=baseline['energy'],
                            energy_improvement=baseline['energy'] - result['energy']))
sources = ['solve.py', 'production.py', 'variational.py', 'window.py', 'fast.py',
           'optimizer.py', 'contractor.py']
summary = dict(validation='public contractor; no hidden evaluator or score',
               valid_runs=len(records), source_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                                       for name in sources}, runs=records)
stress_records = []
for index in range(3):
    stem = Path(f'experiments/stress_{index}')
    request = json.loads(Path(f'{stem}.json').read_text())
    result = json.loads(Path(f'{stem}.measure.json').read_text())
    if Path(f'{stem}.npz').exists():
        actual = measure(load_mps(f'{stem}.npz', request), request)
        assert abs(actual['energy'] - result['energy']) < 1e-10
    user, system, wall, rss = map(float, Path(f'{stem}.time').read_text().split())
    assert user + system < 6 and wall < 30
    stress_records.append(dict(case=request['case_id'], n_sites=request['n_sites'],
                               local_dim=request['local_dim'], bond_cap=request['bond_cap'],
                               sector=request['sector'], valid=True, **result,
                               cpu_seconds=user + system, wall_seconds=wall, max_rss_kib=int(rss)))
summary['stress_valid_runs'] = len(stress_records)
summary['stress_runs'] = stress_records
Path('experiments/summary.json').write_text(json.dumps(summary, indent=2) + '\n')
for record in records:
    print(record['case'], record['budget_seconds'], f"{record['energy']:.12f}",
          f"CPU={record['cpu_seconds']:.2f}", f"delta={record['energy_improvement']:.3g}")
print('Validated runs:', len(records))
print('Validated stress runs:', len(stress_records))

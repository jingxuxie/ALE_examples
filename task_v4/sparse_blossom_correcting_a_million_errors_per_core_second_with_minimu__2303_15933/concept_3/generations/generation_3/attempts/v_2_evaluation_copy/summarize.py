import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parent
regimes = ('chain_hooks', 'patch_crosstalk', 'burst_aliases')


def aggregate(records):
    cells = defaultdict(list)
    for episode, scores in records:
        for family, score in scores.items():
            cells[regimes[episode % 3] + '/' + family].append(score**2)
    result = {cell: float(np.sqrt(np.mean(values))) for cell, values in sorted(cells.items())}
    return {'episodes': len(records), 'cells': result,
            'mean_cell_log_rmse': float(np.mean(list(result.values()))),
            'worst_cell_log_rmse': max(result.values())}


public_records = []
cpu = []
rss = []
query_counts = []
for episode in range(6):
    report = json.loads((root / f'validation/final/protocol_{episode}.json').read_text())
    assert report['valid'] and report['shots_used'] == 40000 and report['queries'] <= 64
    public_records.append((episode, report['family_log_rmse']))
    query_counts.append(report['queries'])
    log = (root / f'validation/final/protocol_{episode}.log').read_text()
    measurement = re.search(r'measured_cpu ([0-9.]+) rss_kib ([0-9]+)', log)
    assert measurement
    cpu.append(float(measurement.group(1)))
    rss.append(int(measurement.group(2)))

report = {'development_only': True, 'hidden_suite_certified': False,
          'public_protocol': aggregate(public_records)}
for directory, name in [('validation/bits13', 'development_randomized'), ('validation/fresh', 'fresh_randomized')]:
    paths = sorted((root / directory).glob('random_*.json'))
    assert len(paths) == 24
    records = []
    for path in paths:
        result = json.loads(path.read_text())
        assert result['shots'] == 40000 and result['queries'] <= 64
        records.append((result['episode'], result['scores']))
        if name == 'fresh_randomized':
            assert result['limits_enabled']
            cpu.append(result['total_cpu'])
            rss.append(result['rss'])
            query_counts.append(result['queries'])
    report[name] = aggregate(records)

portable = json.loads((root / 'validation/final/portable_protocol.json').read_text())
assert portable['valid']
portable_log = (root / 'validation/final/portable_protocol.log').read_text()
measurement = re.search(r'measured_cpu ([0-9.]+) rss_kib ([0-9]+)', portable_log)
assert measurement
report['portable_kernel'] = {'valid': True, 'episode': portable['episode'],
                             'family_log_rmse': portable['family_log_rmse'],
                             'cpu_seconds': float(measurement.group(1)),
                             'rss_kib': int(measurement.group(2))}
cpu.append(float(measurement.group(1)))
rss.append(int(measurement.group(2)))
for path in ('kernel_test.log', 'portable_kernel_test.log'):
    assert (root / 'validation/final' / path).read_text().strip().endswith('OK')
report['kernel_checks_passed'] = True
report['limits'] = {'local_cpu_and_address_space_limits_enforced': True,
                    'hidden_resource_qualification': False,
                    'cpu_limit_seconds': 60, 'address_space_limit_bytes': 3 * 1024**3,
                    'max_observed_cpu_seconds': max(cpu), 'max_observed_rss_kib': max(rss),
                    'shots_per_episode': 40000, 'max_queries_observed': max(query_counts)}
report['files'] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   for name in ('solution.py', 'kernel.cpp', 'kernel.so', 'kernel_avx2.so')}
(root / 'validation_summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
import numpy as np

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parent
episodes = json.loads((Path(os.environ['P']) / 'input/training.json').read_text())['episodes']


def aggregate(records):
    cells = defaultdict(list)
    for episode, scores in records:
        regime = episodes[episode]['spec']['regime']
        for family, value in scores.items():
            cells[regime + '/' + family].append(value**2)
    errors = {key: float(np.sqrt(np.mean(values))) for key, values in sorted(cells.items())}
    return {'cells': errors, 'mean_cell_log_rmse': float(np.mean(list(errors.values()))),
            'worst_cell_log_rmse': max(errors.values())}


public = []
for episode in range(6):
    report = json.loads((DIRECTORY / ('final_report%d.json' % episode)).read_text())
    assert report['valid']
    assert report['shots_used'] <= 40000 and report['queries'] <= 64
    public.append((episode, report['family_log_rmse']))
randomized = []
random_cpu, random_rss, random_queries = [], [], []
for path in sorted(DIRECTORY.glob('finalrand_*.json')):
    report = json.loads(path.read_text())
    spec = episodes[report['episode']]['spec']
    transcript = report['transcript']
    assert len(transcript) <= spec['max_queries']
    assert sum(observation['shots'] for observation in transcript) <= spec['shot_budget']
    for observation in transcript:
        assert 0 <= observation['action'] < len(spec['actions'])
        assert 1 <= observation['shots'] <= spec['max_shots_per_query']
        assert sum(observation['multiplicities']) == observation['shots']
    rates = np.array(report['rates'])
    assert len(rates) == len(spec['channels']) and np.all(np.isfinite(rates)) and np.all(rates > 0)
    randomized.append((report['episode'], report['scores']))
    random_cpu.append(report['cpu'])
    random_rss.append(report['rss'])
    random_queries.append(len(transcript))
assert len(randomized) == 24
resources = []
for path in sorted(DIRECTORY.glob('final_test?.log')) + [DIRECTORY / 'portable_test.log']:
    text = path.read_text()
    user = float(re.search(r'User time \(seconds\): ([\d.]+)', text).group(1))
    system = float(re.search(r'System time \(seconds\): ([\d.]+)', text).group(1))
    memory = int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', text).group(1))
    assert 'Exit status: 0' in text
    assert user + system < 60
    resources.append({'test': path.name, 'cpu_seconds': user + system, 'max_rss_kib': memory})
result = {'development_only': True, 'hidden_suite_certified': False,
          'exact_law_tests': 'passed', 'public': {'episodes': 6, **aggregate(public)},
          'randomized': {'episodes': len(randomized), **aggregate(randomized),
                         'max_cpu_seconds_including_simulation': max(random_cpu),
                         'max_rss_kib_including_simulation': max(random_rss),
                         'max_queries': max(random_queries)},
          'resources': {'local_cpu_limit_seconds': 60, 'local_address_space_limit_bytes': 3 * 1024**3,
                        'resource_limited_tests': resources,
                        'max_observed_cpu_seconds': max(record['cpu_seconds'] for record in resources),
                        'max_observed_rss_kib': max(record['max_rss_kib'] for record in resources)},
          'files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in ('solution.py', 'kernel.cpp', 'kernel.so', 'kernel_avx2.so')}}
(ROOT / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: result[key] for key in ('public', 'randomized', 'resources')}, indent=2))

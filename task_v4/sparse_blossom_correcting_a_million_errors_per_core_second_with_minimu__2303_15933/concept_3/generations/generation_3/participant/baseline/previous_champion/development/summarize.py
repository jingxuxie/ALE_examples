import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'development' / 'results'
REGIMES = ['chain_hooks', 'patch_crosstalk', 'burst_aliases']


def load(pattern, expected):
    paths = sorted(RESULTS.glob(pattern))
    assert len(paths) == expected, (pattern, len(paths), expected)
    return [json.loads(path.read_text()) for path in paths]


def summarize(reports, public=False):
    cells = {}
    for index, report in enumerate(reports):
        episode = index if public else report['episode']
        scores = report['family_log_rmse'] if public else report['scores']
        for family, value in scores.items():
            cells.setdefault(REGIMES[episode % 3] + '/' + family, []).append(value ** 2)
        if public:
            assert report['valid']
            assert report['shots_used'] == 40000 and report['queries'] <= 64
        else:
            assert sum(shots for action, shots in report['allocations']) == 40000
            assert len(report['allocations']) <= 64
            assert all(0 < shots <= 4000 for action, shots in report['allocations'])
            assert all(math.isfinite(rate) and rate > 0 for rate in report['estimates'])
            assert report['cpu'] < 60
    cells = {key: math.sqrt(sum(values) / len(values)) for key, values in sorted(cells.items())}
    return dict(episodes=len(reports), cells=cells, mean_cell_log_rmse=sum(cells.values()) / len(cells),
                worst_cell_log_rmse=max(cells.values()))


public = load('submission_public[0-5].json', 6)
randomized = load('submission_[0-5]_[4-7].json', 24)
stress = load('submission_stress20_[0-5].json', 6)
summary = dict(development_only=True, hidden_suite_certified=False,
               public=summarize(public, public=True), randomized=summarize(randomized),
               synthetic_20_detector_stress=summarize(stress),
               limits=dict(cpu_seconds=60, address_space_bytes=3 * 1024 ** 3,
                           max_observed_cpu_seconds=max(report['cpu'] for report in randomized + stress),
                           max_observed_rss_kib=max(report['maxrss_kib'] for report in randomized + stress)),
               files={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in ['solution.py', 'kernel.cpp', 'kernel.so', 'kernel_avx2.so']})
(ROOT / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))

import json
from pathlib import Path
import sys


def score(payload):
    result = payload['diagnostic']
    return (max(result['plateau_spread'] - .003, 0)
            + 20 * max(.0155 - result['retained_optical_min'], 0)
            + max(.11 - result['gap_lower_bound'], 0)
            + max(.20 - result['plateau_mean'], 0)
            + max(result['plateau_mean'] - .41, 0)
            + abs(result['full'] - 1)
            + .01 * result['plateau_spread'])


paths = [Path(filename) for filename in sys.argv[1:]] or list(Path('.').glob('refined_*.json'))
records = [(path, json.loads(path.read_text())) for path in paths]
records.sort(key=lambda pair: score(pair[1]))
for path, record in records:
    result = record['diagnostic']
    print(path, score(record), result['plateau_spread'], result['plateau_mean'],
          result['retained_optical_min'], result['gap_lower_bound'], flush=True)
best_path, best = records[0]
Path('witness.json').write_text(json.dumps({'parameters': best['parameters']}, indent=2, allow_nan=False) + '\n')
print('Selected', best_path, flush=True)

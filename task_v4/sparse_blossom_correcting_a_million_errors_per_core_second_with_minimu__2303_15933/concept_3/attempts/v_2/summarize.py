import json
import sys
import numpy as np

for path in sys.argv[1:]:
    records = json.load(open(path))
    print(path, len(records))
    keys = ['risks']
    if 'posterior_risks' in records[0]:
        keys.append('posterior_risks')
    for key in keys:
        pooled = []
        for regime in sorted(set(record['regime'] for record in records)):
            errors = np.array([record[key] for record in records if record['regime'] == regime])
            cells = np.sqrt(np.mean(errors ** 2, axis=0))
            pooled.extend(cells)
            print(key, regime, cells.round(5).tolist())
        print('mean', round(np.mean(pooled), 6), 'max', round(np.max(pooled), 6),
              'cpu max', round(max(record['cpu'] for record in records), 2))
    if 'posterior_errors' in records[0]:
        for mix in (0.25, 0.5, 0.75, 1.0):
            pooled = []
            for regime in sorted(set(record['regime'] for record in records)):
                errors = np.array([(1 - mix) * np.array(record['errors']) + mix * np.array(record['posterior_errors'])
                                   for record in records if record['regime'] == regime])
                boundary_count = (errors.shape[1] - 10) // 2
                splits = [0, boundary_count, 2 * boundary_count + 2, 2 * boundary_count + 6, errors.shape[1]]
                pooled.extend(np.sqrt(np.mean(errors[:, lower:upper] ** 2)) for lower, upper in zip(splits[:-1], splits[1:]))
            print('mix', mix, 'mean', round(np.mean(pooled), 6), 'max', round(np.max(pooled), 6))

import glob
import json
import os
from pathlib import Path

from engine import Samples


patterns = set()
for filename in glob.glob('*.jsonl'):
    for line in Path(filename).read_text().splitlines():
        try:
            record = json.loads(line)
            if 'z_image' in record:
                patterns.add(tuple(record['z_image']))
        except json.JSONDecodeError:
            pass
for filename in glob.glob('mixed*.raw'):
    for line in Path(filename).read_text().splitlines():
        pattern = line.split()[0]
        patterns.add(tuple(map(int, pattern)))
for filename in ['design.json', os.environ['P'] + '/baseline/design.json']:
    patterns.add(tuple(json.loads(Path(filename).read_text())['z_image']))
cache_path = Path('candidate_scores.json')
cache = json.loads(cache_path.read_text()) if cache_path.exists() else []
known = {tuple(record['z_image']) for record in cache}
samples = [[Samples(scale, 99712341 + 37 * scale + density_index, 8192, density) for density_index, density in enumerate([.28, .30, .32])] for scale in range(1, 4)]
for pattern in sorted(patterns - known):
    record = {'z_image': list(pattern), 'groups': []}
    for scale_samples in samples:
        record['groups'].append([sample.score(pattern) for sample in scale_samples])
        mean = sum(sum(group) / 3 for group in record['groups'])
        record['upper_core'] = (mean + 3 - len(record['groups'])) / 3
        if record['upper_core'] < .825:
            break
    if len(record['groups']) == 3:
        record['core_score'] = record['upper_core']
        record['worst_group'] = min(value for group in record['groups'] for value in group)
        print(json.dumps(record), flush=True)
    cache.append(record)
    cache_path.write_text(json.dumps(cache, indent=2) + '\n')
print('patterns', len(patterns), 'evaluated', len(cache), flush=True)
print('top', sorted((record for record in cache if 'core_score' in record), key=lambda record: record['core_score'], reverse=True)[:5], flush=True)

import json
import subprocess
from pathlib import Path

patterns = set()
for filename, count in [('matching_scores.txt', 16), ('defect2_scores.txt', 12)]:
    for line in Path(filename).read_text().splitlines()[:count]:
        patterns.add(line.split()[1])
for filename in Path('.').glob('branch*.log'):
    for line in filename.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in ['POOL', 'BEST']:
            patterns.add(fields[2])
cache = Path('candidate_validation.json')
results = json.loads(cache.read_text()) if cache.exists() else []
evaluated = {result['pattern'] for result in results}
for pattern in sorted(patterns - evaluated):
    text = subprocess.check_output(['./optimize', 'eval', '93719623', pattern, '1024'], text=True)
    lines = text.splitlines()
    fields = lines[-1].split()
    result = {'pattern': pattern, 'core': float(fields[1]), 'worst': float(fields[3]),
              'groups': [list(map(float, line.split())) for line in lines[1:10]]}
    results.append(result)
    print(pattern, result['core'], result['worst'], flush=True)
    Path('candidate_validation.json').write_text(json.dumps(sorted(results, key=lambda item: -item['core']), indent=2) + '\n')

import json
from pathlib import Path

suite = json.loads(Path('dev/instances.json').read_text())
with Path('dev/instances.txt').open('w') as output:
    output.write(str(len(suite['instances'])) + '\n')
    for case in suite['instances']:
        output.write(f"{case['id']} {case['n']} {len(case['edges'])} {len(case['required_parities'])} {case['max_cnots']} {case['max_depth']}\n")
        for edge in case['edges']:
            output.write(' '.join(map(str, edge)) + '\n')
        output.write(' '.join(map(str, case['target_rows'])) + '\n')
        output.write(' '.join(map(str, case['required_parities'])) + '\n')

import json
import time
from pathlib import Path
from api import robust_screen

started = time.monotonic()
source = json.loads(Path('rotated.json').read_text())
result = robust_screen(source['pair_matrix'], source['amplitudes'], check_paths=True)
Path('validation.json').write_text(json.dumps(result, indent=2)+'\n')
summary = {key:value for key,value in result.items() if key != 'points'}
summary['runtime_seconds'] = time.monotonic()-started
print(json.dumps(summary, indent=2), flush=True)
Path('validation_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
if result['passed']:
    Path('submission.json').write_text(json.dumps(source, indent=2, allow_nan=False)+'\n')
    print('Saved validated submission.json', flush=True)

import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
checker = root.parents[1] / 'participant/workspace/check.py'
artifact = root / (sys.argv[1] if len(sys.argv) > 1 else 'state.npz')
completed = subprocess.run([sys.executable, str(checker), str(artifact)], capture_output=True, text=True, check=True)
result = json.loads(completed.stdout)
(root / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
summary = {key: value for key, value in result.items() if key != 'metrics'}
summary['metrics'] = {key: value for key, value in result.get('metrics', {}).items() if not isinstance(value, list)}
print(json.dumps(summary, indent=2))

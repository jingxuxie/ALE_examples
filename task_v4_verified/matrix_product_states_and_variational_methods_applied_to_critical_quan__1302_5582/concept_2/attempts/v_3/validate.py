import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / 'participant' / 'workspace'))
from physics import check

for name in sys.argv[1:] or ['state.npz']:
    path = Path(name)
    result = check(path)
    path.with_suffix('.check.json').write_text(json.dumps(result, indent=2) + '\n')
    summary = dict(result)
    if 'metrics' in summary:
        summary['metrics'] = {key: value for key, value in result['metrics'].items() if not isinstance(value, list)}
    print(name, json.dumps(summary, indent=2), flush=True)

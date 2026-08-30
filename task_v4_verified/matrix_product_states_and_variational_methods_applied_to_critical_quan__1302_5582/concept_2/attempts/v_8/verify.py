import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'participant' / 'workspace'))
from physics import check

parser = argparse.ArgumentParser()
parser.add_argument('tensor')
parser.add_argument('--output', default='verification.json')
arguments = parser.parse_args()
started = time.monotonic()
result = check(arguments.tensor)
result['runtime_seconds'] = time.monotonic() - started
with open(arguments.output, 'w') as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
summary = {key: value for key, value in result.items() if key != 'metrics'}
summary['metrics'] = {key: value for key, value in result.get('metrics', {}).items() if not isinstance(value, list)}
print(json.dumps(summary, indent=2, allow_nan=False))

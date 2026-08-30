import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import sys
import time
from pathlib import Path

output = Path(__file__).resolve().parent
root = output.parents[1] / 'participant'
sys.path.insert(0, str(root / 'workspace'))
from search_api import assess, parse_submission

while True:
    try:
        if '\nFINAL ' in (output / 'optimize.log').read_text():
            break
    except FileNotFoundError:
        pass
    time.sleep(5)

parameters = parse_submission((output / 'submission.json').read_text())
started = time.monotonic()
cpu_started = time.process_time()
print('Starting exhaustive supplied assessment', flush=True)
result = assess(parameters, exhaustive=True)
result['runtime_seconds'] = time.monotonic() - started
result['cpu_seconds'] = time.process_time() - cpu_started
(output / 'validation.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
print(json.dumps({key: value for key, value in result.items() if key not in ('family', 'certificate_screen', 'skipped_members')}, indent=2), flush=True)
for key in ('certificate', 'tail_mass', 'mass_drift', 'energy_drift'):
    print(key, max((member[key], member['name']) for member in result['family']), flush=True)
print('minimum_conservative_density_gap', min((member['conservative_density_gap'], member['name']) for member in result['family']), flush=True)

import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import json
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(ROOT / 'workspace'))
from search_api import family, PROTOCOL
from simulator import quick, integrate, diagnostics

output = Path(__file__).resolve().parent
parameters = json.loads((ROOT / 'baseline/champion.json').read_text())['parameters']
started = time.process_time()
reports = {}
for name, member in family(parameters):
    report = quick(member)
    coarse = diagnostics(member, integrate(member, 32, 512))
    for key in ('mass_drift', 'energy_drift'):
        report[key] = max(report[key], coarse[key])
    reports[name] = report
    margin = min(report['observable_gap'] / .3, *(limit / report[key] for key, limit in PROTOCOL['limits'].items()))
    print(name, 'margin', round(margin, 6), json.dumps(report), flush=True)
    (output / 'baseline_screen.json').write_text(json.dumps(reports, indent=2))
print('cpu_seconds', time.process_time() - started, flush=True)

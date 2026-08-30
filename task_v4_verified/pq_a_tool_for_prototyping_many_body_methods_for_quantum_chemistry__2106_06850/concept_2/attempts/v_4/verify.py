import argparse
import json
import time
from pathlib import Path
from api import robust_screen
from oracle import DeterminantCC

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('--paths', action='store_true')
parser.add_argument('--output', default='verification.json')
arguments = parser.parse_args()
started = time.monotonic()
data = json.loads(Path(arguments.filename).read_text())
report = robust_screen(data['pair_matrix'], data['amplitudes'], oracle=DeterminantCC(), check_paths=arguments.paths)
report['runtime_seconds'] = time.monotonic() - started
Path(arguments.output).write_text(json.dumps(report,indent=2,allow_nan=False))
print({key:value for key,value in report.items() if key not in ['points','adaptive_response']},flush=True)
if 'points' in report:
    print('failures',[(point['point'],point['failures']) for point in report['points'] if point['failures']],flush=True)

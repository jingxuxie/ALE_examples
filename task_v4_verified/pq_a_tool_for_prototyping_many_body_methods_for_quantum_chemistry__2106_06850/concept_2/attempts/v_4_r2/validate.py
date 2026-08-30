import argparse
import json
import time
from pathlib import Path
import numpy as np
from api import robust_screen, check_continuation
from oracle import DeterminantCC

parser=argparse.ArgumentParser()
parser.add_argument('input',type=Path)
parser.add_argument('--endpoints',action='store_true')
parser.add_argument('--base-path',action='store_true')
arguments=parser.parse_args()
submission=json.loads(arguments.input.read_text())
started=time.time()
if arguments.base_path:
    report=check_continuation(submission['pair_matrix'],submission['amplitudes'])
    print({key:min(row[key] for row in report['history']) for key in ['gap','overlap','jacobian_singular_min']})
    print('passed',report['passed'],'endpoint_error',report.get('endpoint_error'))
else:
    report=robust_screen(submission['pair_matrix'],submission['amplitudes'],check_paths=not arguments.endpoints)
    print(json.dumps({key:value for key,value in report.items() if key not in ['points','adaptive_response']}),flush=True)
    print('gradient',report.get('adaptive_response',{}).get('norm'),flush=True)
    if 'points' in report:
        failed=[point for point in report['points'] if point['failures']]
        print('failed_count',len(failed),'first',failed[:8],flush=True)
arguments.input.with_suffix('.validation.json').write_text(json.dumps(report,indent=2))
print('seconds',time.time()-started,flush=True)

import os
for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[variable]='1'
import json
import sys
import time
from pathlib import Path
import numpy as np
from api import robust_screen, check_continuation, CONSTRAINTS
from oracle import DeterminantCC

source=Path(sys.argv[1])
prefix=sys.argv[2] if len(sys.argv)>2 else 'validation'
payload=json.loads(source.read_text())
Path(prefix+'.artifact.json').write_text(json.dumps(payload,indent=2))
matrix=np.array(payload['pair_matrix'])
amplitudes=np.array(payload['amplitudes'])
oracle=DeterminantCC()
started=time.time()
endpoint=robust_screen(matrix,amplitudes,oracle,check_paths=False)
Path(prefix+'.endpoints.json').write_text(json.dumps(endpoint,indent=2))
print({key:value for key,value in endpoint.items() if key!='points'},flush=True)
print('failed points',[point for point in endpoint.get('points',[]) if point['failures']][:12],flush=True)
path=check_continuation(matrix,amplitudes,oracle)
Path(prefix+'.basepath.json').write_text(json.dumps(path,indent=2))
print('base path',{key:value for key,value in path.items() if key!='history'},flush=True)
if path['history']:
    print('path extrema', {key:min(row[key] for row in path['history']) for key in ['gap','overlap','jacobian_singular_min']},max(row['amplitude_step'] for row in path['history']),flush=True)
if endpoint.get('endpoint_feasible') and path['passed']:
    result=robust_screen(matrix,amplitudes,oracle,check_paths=True)
    Path(prefix+'.full.json').write_text(json.dumps(result,indent=2))
    print('FULL',{key:value for key,value in result.items() if key!='points'},flush=True)
    if result['passed']:
        Path('submission.json').write_text(json.dumps(payload,indent=2))
print('seconds',time.time()-started,flush=True)

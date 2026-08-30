import os
import sys
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import resource
import subprocess
import time
from pathlib import Path
from contractor import load_mps, measure

root = Path(__file__).resolve().parent.parent
work = root/'experiments'
cases = ['symmetric', 'odd', 'nonuniform', 'critical', 'critical_odd', 'broken',
         'broken_odd', 'alternating', 'alternating_odd', 'weak', 'weak_odd',
         'stress0_', 'stress1_', 'stress2_', 'stress3_']
if len(sys.argv) > 1:
    cases = sys.argv[1:]
results = []
for case in cases:
    for budget in [6, 40]:
        request_path = work/(case+str(budget)+'.json')
        request = json.loads(request_path.read_text())
        state_path = work/('validated_'+case+str(budget)+'.npz')
        log_path = work/('validated_'+case+str(budget)+'.log')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (budget, budget))
            resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
            resource.setrlimit(resource.RLIMIT_FSIZE, (8388608, 8388608))
        environment = dict(os.environ)
        environment.pop('MPS_DEBUG', None)
        start = time.monotonic()
        with log_path.open('wb') as log:
            process = subprocess.Popen([sys.executable, str(root/'solve.py'), '--request', str(request_path), '--output', str(state_path)],
                cwd=root, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=log, preexec_fn=limits)
            while True:
                child, status, usage = os.wait4(process.pid, os.WNOHANG)
                if child:
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                if time.monotonic()-start > request['wall_seconds']:
                    process.kill()
                    child, status, usage = os.wait4(process.pid, 0)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(.025)
        result = dict(case=case, budget=budget, cpu_seconds=usage.ru_utime+usage.ru_stime,
            wall_seconds=time.monotonic()-start, max_rss_bytes=usage.ru_maxrss*1024,
            returncode=process.returncode)
        if process.returncode == 0:
            result.update(measure(load_mps(state_path, request), request))
            result['state_bytes'] = state_path.stat().st_size
        else:
            result['error'] = log_path.read_text()
        results.append(result)
        (work/'validation_results.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(result), flush=True)
        assert process.returncode == 0, result
        assert result['cpu_seconds'] < budget, result
print('ALL VALID', len(results), flush=True)

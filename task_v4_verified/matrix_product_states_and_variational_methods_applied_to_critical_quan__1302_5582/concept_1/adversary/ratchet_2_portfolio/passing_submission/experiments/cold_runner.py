import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import math
import resource
import subprocess
import time
from pathlib import Path
from contractor import load_mps, measure

budget = float(sys.argv[1])
report_path = Path(sys.argv[2])
results = []
for filename in sys.argv[3:]:
    request = json.loads(Path(filename).read_text())
    request['budget_seconds'] = budget
    request['wall_seconds'] = 30. if budget <= 6 else 120.
    stem = Path(filename).stem + '_cold_' + str(int(budget))
    request_path = Path('experiments') / (stem + '.json')
    output_path = Path('experiments') / (stem + '.npz')
    log_path = Path('experiments') / (stem + '.log')
    request_path.write_text(json.dumps(request))
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2**31, 2**31))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8*2**20, 8*2**20))
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(budget), math.ceil(budget)))
    start = time.monotonic()
    with log_path.open('wb') as stream:
        process = subprocess.Popen([sys.executable, 'solve.py', '--request', str(request_path),
                                    '--output', str(output_path)], stdout=stream,
                                   stderr=subprocess.STDOUT, preexec_fn=limits)
        while True:
            waited, status, usage = os.wait4(process.pid, os.WNOHANG)
            if waited:
                break
            if time.monotonic()-start > request['wall_seconds']:
                process.kill()
                waited, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(.025)
        process.returncode = os.waitstatus_to_exitcode(status)
    elapsed = time.monotonic()-start
    cpu = usage.ru_utime+usage.ru_stime
    result = dict(case=request['case_id'], budget=budget, cpu=cpu, wall=elapsed,
                  returncode=process.returncode, max_rss_kib=usage.ru_maxrss,
                  valid=False)
    try:
        assert process.returncode == 0, log_path.read_text()
        assert cpu <= budget and elapsed <= request['wall_seconds'], 'Budget exceeded'
        result.update(measure(load_mps(output_path, request), request))
        result['valid'] = True
    except Exception as error:
        result['error'] = str(error)
    results.append(result)
    report_path.write_text(json.dumps(results, indent=2))
    print(json.dumps(result), flush=True)

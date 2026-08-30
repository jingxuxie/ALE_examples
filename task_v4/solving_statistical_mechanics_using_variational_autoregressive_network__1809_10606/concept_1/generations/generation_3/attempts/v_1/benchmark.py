import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import resource
import subprocess
import sys
import time
from pathlib import Path
from audit import metrics


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024 ** 3, 8 * 1024 ** 3))
    try:
        available = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, available[:4])
    except PermissionError:
        pass


results_path = Path(sys.argv[1])
results = []
for argument in sys.argv[2:]:
    instance_path = Path(argument).resolve()
    destination = Path('verified_' + instance_path.stem + '.json').resolve()
    log_path = destination.with_suffix('.log')
    environment = os.environ.copy()
    environment['SOLVE_VERBOSE'] = '1'
    started = time.monotonic()
    with log_path.open('w') as output:
        completed = subprocess.run([sys.executable, 'solve.py', str(instance_path), str(destination)],
                                   stdout=output, stderr=subprocess.STDOUT, env=environment,
                                   timeout=120, preexec_fn=limits)
    elapsed = time.monotonic() - started
    if completed.returncode:
        raise RuntimeError(log_path.read_text())
    assert destination.stat().st_size <= 1048576
    result = metrics(json.loads(instance_path.read_text()), json.loads(destination.read_text()))
    result.update({'case': instance_path.stem, 'seconds': elapsed,
                   'peak_child_mib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024})
    results.append(result)
    results_path.write_text(json.dumps(results, indent=2))
    print(json.dumps(result), flush=True)

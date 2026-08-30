import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import time


resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024 ** 2, 2048 * 1024 ** 2))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
start = time.perf_counter()

import numpy as np

from exact import LOWER, evaluate
from finalize import GATES, structural


source = Path('witness.json')
witness = json.loads(source.read_text())
structural(witness)
report, details = evaluate(witness, True)
gradient = details[-1][LOWER]
coordinates = sorted(set([0, 20, 55, 90, 119, int(np.argmax(np.abs(gradient)))]))
checks = []
epsilon = 1e-5
for coordinate in coordinates:
    row, column = int(LOWER[0][coordinate]), int(LOWER[1][coordinate])
    plus = copy.deepcopy(witness)
    minus = copy.deepcopy(witness)
    plus['weights'][row][column] += epsilon
    minus['weights'][row][column] -= epsilon
    finite_difference = (evaluate(plus)['reverse_kl'] - evaluate(minus)['reverse_kl']) / (2 * epsilon)
    checks.append({'row': row, 'column': column, 'analytic': float(gradient[coordinate]),
                   'finite_difference': finite_difference,
                   'absolute_error': abs(finite_difference - gradient[coordinate])})
maximum_error = float(max(check['absolute_error'] for check in checks))
assert maximum_error < 1e-7
assert abs(report['normalization'] - 1) <= 1e-10
assert report['symmetry_error'] <= 1e-12
assert source.is_file() and not source.is_symlink() and source.stat().st_size <= 131072
usage = resource.getrusage(resource.RUSAGE_SELF)
wall = time.perf_counter() - start
cpu = usage.ru_utime + usage.ru_stime
assert wall < 120 and cpu < 120
failing = [key for key, (threshold, lower) in GATES.items()
           if (report[key] < threshold - 1e-10 if lower else report[key] > threshold + 1e-10)]
result = {
    'structurally_valid': True,
    'enumerated_configurations': 65536,
    'metric_gates_pass': not failing,
    'failing_gates': failing,
    'core_score': report['core_score'],
    'gradient_finite_difference_checks': checks,
    'maximum_gradient_finite_difference_error': maximum_error,
    'wall_seconds': wall,
    'cpu_seconds': cpu,
    'peak_rss_mib': usage.ru_maxrss / 1024,
    'address_space_limit_mib': 2048,
    'cpu_limit_seconds': 120,
    'json_bytes': source.stat().st_size,
    'witness_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
}
Path('submission_check.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps(result, indent=2))

import os
import sys
import time

STARTED = time.monotonic()
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import math
from pathlib import Path
import numpy as np
from search import solve_case


def orthogonalize(matrix):
    left, _, right = np.linalg.svd(matrix, full_matrices=False)
    return left @ right


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    cases = request['cases']
    seconds_per_case = float(request.get('seconds_per_case', 10.0))
    if not math.isfinite(seconds_per_case) or seconds_per_case <= 0:
        seconds_per_case = 10.0
    total_budget = min(173.0, .90 * seconds_per_case * len(cases))
    deadline = STARTED + total_budget
    solutions = []
    for index, case in enumerate(cases):
        remaining = (deadline - time.monotonic() - .10) / (len(cases) - index)
        budget = max(.005, min(.90 * seconds_per_case, remaining))
        _, orbital, auxiliary = solve_case(case, seconds=budget)
        solutions.append({'id': case['id'], 'orbital': orthogonalize(orbital).tolist(),
                          'auxiliary': orthogonalize(auxiliary).tolist()})
    Path(sys.argv[2]).write_text(json.dumps({'solutions': solutions}, allow_nan=False))


if __name__ == '__main__':
    main()

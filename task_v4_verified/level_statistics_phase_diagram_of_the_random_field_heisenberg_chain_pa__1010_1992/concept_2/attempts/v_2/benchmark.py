import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_2/participant')
sys.path.insert(0, str(ROOT / 'workspace'))
from physics import observables

spec = json.loads((ROOT / 'input/spec.json').read_text())
generator = np.random.default_rng(142)
with threadpool_limits(1):
    for bank in spec['banks']:
        fields = np.array(bank['fields'])
        sorted_order = np.argsort(fields)
        patterns = [sorted_order, sorted_order[[0, 2, 4, 6, 8, 10, 11, 9, 7, 5, 3, 1]],
                    sorted_order[[0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11]]]
        patterns += [generator.permutation(12) for trial in range(15)]
        for order in patterns:
            start = time.monotonic()
            result = observables(fields[order])
            print(bank['id'], order.tolist(), result, 'sec', time.monotonic() - start, flush=True)

import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'

from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

import numpy as np

from generators import sample_cases
from reference_physics import observables, sector


def initialize():
    sector(10)
    sector(12)


def label(case):
    return dict(case, f=observables(case['fields'])['f'])


if __name__ == '__main__':
    started = time.perf_counter()
    with ProcessPoolExecutor(4, initializer=initialize) as executor:
        for split in (1, 2):
            cases = sample_cases(40, np.random.default_rng(873291 + split))
            path = Path(f'independent_{split}.jsonl')
            with path.open('w') as stream:
                for index, record in enumerate(executor.map(label, cases, chunksize=1)):
                    stream.write(json.dumps(record) + '\n')
                    stream.flush()
                    if (index + 1) % 80 == 0:
                        print(split, index + 1, time.perf_counter() - started, flush=True)

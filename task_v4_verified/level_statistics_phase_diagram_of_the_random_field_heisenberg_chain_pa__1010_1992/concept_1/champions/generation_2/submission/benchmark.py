import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import time
import numpy as np
from generators import sample_fields
from physics import observables
fields = sample_fields(np.random.default_rng(9), 14, 'shuffled_pairs')
started = time.monotonic()
print(observables(fields), time.monotonic() - started, flush=True)
print('affinity', os.sched_getaffinity(0), flush=True)

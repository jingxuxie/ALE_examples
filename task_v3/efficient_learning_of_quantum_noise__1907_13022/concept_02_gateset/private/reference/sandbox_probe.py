import os
from pathlib import Path
import sys

import numpy as np
import scipy.linalg


for prefix in ('/home/xuandong', '/srv/home/xuandong'):
    private = Path(prefix) / 'mnt/jingxu/ALE/tasks_v3/efficient_learning_of_quantum_noise__1907_13022'
    forbidden = private / 'concept_02_gateset/private/reference/core/local_edges_01/oracle.npz'
    try:
        with forbidden.open('rb') as stream:
            stream.read(1)
    except PermissionError:
        pass
    else:
        raise RuntimeError('Private oracle was accessible')
for variable in ('HOME', 'TMPDIR', 'NUMBA_CACHE_DIR'):
    directory = Path(os.environ[variable])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (variable + '.probe')).write_text('temporary filesystem allowed')
scipy.linalg.svd(np.eye(2))
with np.load(sys.argv[1], allow_pickle=False) as data:
    queries = len(data['query_ptr']) - 1
    heldout = len(data['holdout_observable'])
np.savez_compressed(sys.argv[2], structural_identifiable=np.zeros(queries),
                    calibration_identifiable=np.zeros(queries), query_log_estimate=np.zeros(queries),
                    holdout_mean=np.zeros(heldout))

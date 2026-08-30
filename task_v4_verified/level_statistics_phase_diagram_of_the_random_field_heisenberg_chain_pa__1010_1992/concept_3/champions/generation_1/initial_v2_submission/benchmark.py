import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import sys
import time
import numpy as np
from scipy.linalg import eigvals_banded, eigh
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import reverse_cuthill_mckee
sys.path.insert(0, '../../participant/workspace')
import exact

states, spins, exchange = exact.sector()
permutation = reverse_cuthill_mckee(csr_matrix(exchange), symmetric_mode=True)
matrix = exchange[permutation][:, permutation]
rows, columns = np.nonzero(matrix)
bandwidth = int(np.max(np.abs(rows-columns)))
print('bandwidth', bandwidth, flush=True)
banded = np.zeros((bandwidth+1, len(states)), order='F')
for distance in range(bandwidth+1):
    banded[distance, :len(states)-distance] = np.diag(matrix, -distance)
random = np.random.default_rng(1992)
fields = random.uniform(-3,3,12)
fields -= fields.mean()
reference = exact.spectrum(fields)
for mode in ['evr','evd','banded']:
    started = time.monotonic()
    for iteration in range(10):
        if mode == 'banded':
            working = banded.copy(order='F')
            working[0] += spins[permutation] @ fields
            energies = eigvals_banded(working, lower=True, overwrite_a_band=True, check_finite=False)
        else:
            energies = exact.spectrum(fields, driver=mode)
    print(mode, (time.monotonic()-started)/10, np.max(np.abs(energies-reference)), flush=True)

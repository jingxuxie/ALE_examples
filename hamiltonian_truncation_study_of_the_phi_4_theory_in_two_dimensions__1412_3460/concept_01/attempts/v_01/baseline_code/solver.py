import time

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh

from cutoff import correction
from io_archive import load_archive
from normal_order import physical_couplings


def solve(case, archive, cutoff, method='production'):
    started = time.perf_counter()
    manifest, sectors = load_archive(archive, cutoff)
    couplings, constant = physical_couplings(case)
    result = {}
    for label, sector in sectors.items():
        hamiltonian = sparse.diags(sector['energy'], format='csr')
        for key, coupling in couplings.items():
            if key in sector['operators']:
                hamiltonian = hamiltonian + coupling * sector['operators'][key]
        hamiltonian = hamiltonian + correction(case, sector, cutoff, method)
        count = min(3, hamiltonian.shape[0])
        if hamiltonian.shape[0] <= 180:
            energies = linalg.eigh(hamiltonian.toarray(), eigvals_only=True,
                                   subset_by_index=(0, count - 1))
        else:
            energies = np.sort(eigsh(hamiltonian, k=count, which='SA',
                                     return_eigenvectors=False, tol=1e-9,
                                     v0=np.ones(hamiltonian.shape[0])))
        result[label] = (energies + constant).tolist()
    return {'case': case['id'], 'cutoff': cutoff, 'method': method,
            'levels': result, 'seconds': time.perf_counter() - started,
            'dimension': sum(len(sector['energy']) for sector in sectors.values())}

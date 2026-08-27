import math
import time

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh

from archive import load_archive
from physics import circle_couplings, finite_volume, spectral_coefficients
from renormalization import local_matrix, state_correction


def diagonalize(hamiltonian, count=3):
    count = min(count, hamiltonian.shape[0])
    if hamiltonian.shape[0] <= 180:
        values, vectors = linalg.eigh(hamiltonian.toarray(), subset_by_index=(0, count - 1))
    else:
        values, vectors = eigsh(hamiltonian, k=count, which='SA', tol=2e-11,
                               v0=np.random.default_rng(1337).normal(size=hamiltonian.shape[0]))
        order = np.argsort(values)
        values, vectors = values[order], vectors[:, order]
    return values, vectors


def solve(case, archive, cutoff, method='improved'):
    start = time.perf_counter()
    manifest, sectors = load_archive(archive, cutoff)
    couplings, contraction, casimir = circle_couplings(case)
    gaussian = all(term['degree'] == 2 and term.get('transfer', 0) == 0 for term in case['couplings'])
    if method == 'improved' and gaussian:
        physical_mass = math.sqrt(case['mass']**2 + 2 * sum(term['value'] for term in case['couplings']))
        density = (physical_mass**2 * (1 - math.log(physical_mass**2 / case['mass']**2)) - case['mass']**2) / (8 * math.pi)
        vacuum = density * case['length'] + finite_volume(case['length'], physical_mass, case['boundary'])[1]
        from basis import enumerate_basis
        result = {}
        for sector in manifest['sectors']:
            energies = enumerate_basis(case['length'], physical_mass, 8 * physical_mass,
                                       case['boundary'], sector['momentum'], sector['parity'])[3]
            result[sector['name']] = (energies[:3] + vacuum).tolist()
        return {'case': case['id'], 'cutoff': cutoff, 'method': method, 'levels': result,
                'seconds': time.perf_counter() - start,
                'dimension': sum(len(sector['energy']) for sector in sectors.values())}
    coefficients = spectral_coefficients(couplings, contraction)
    constant = casimir + couplings.get((0, 0), 0.0) * case['length']
    raw = {}
    hamiltonians = {}
    for label, sector in sectors.items():
        hamiltonian = sparse.diags(sector['energy'], format='csr')
        for key, coupling in couplings.items():
            if key[0] and key in sector['operators']:
                hamiltonian = hamiltonian + coupling * sector['operators'][key]
        hamiltonians[label] = hamiltonian
        raw[label] = diagonalize(hamiltonian)
    reference = min(values[0] for values, vectors in raw.values())
    result = {}
    for label, sector in sectors.items():
        energies, vectors = raw[label]
        if method != 'raw':
            correction = local_matrix(sector['operators'], coefficients, cutoff, case['mass'], reference)
            energies, vectors = diagonalize(hamiltonians[label] + correction)
            if method == 'improved':
                energies = np.asarray([energy + state_correction(
                    sector['operators'], coefficients, sector['energy'], vectors[:, index], cutoff,
                    case['mass'], energy, reference) for index, energy in enumerate(energies)])
        result[label] = (energies + constant).tolist()
    return {'case': case['id'], 'cutoff': cutoff, 'method': method, 'levels': result,
            'seconds': time.perf_counter() - start,
            'dimension': sum(len(sector['energy']) for sector in sectors.values())}

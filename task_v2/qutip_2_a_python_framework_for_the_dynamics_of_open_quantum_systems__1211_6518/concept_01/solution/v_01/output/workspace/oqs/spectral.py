import numpy as np
from scipy.linalg import expm

from .baths import spectrum


def dissipator(operator):
    dimension = len(operator)
    identity = np.eye(dimension)
    gram = operator.conj().T @ operator
    return np.kron(operator.conj(), operator) - (np.kron(identity, gram) + np.kron(gram.T, identity)) / 2


def evolve_generator(generator, initial, elapsed):
    dimension = len(initial)
    vector = initial.reshape(-1, order='F')
    return np.asarray([(expm(generator * time) @ vector).reshape(dimension, dimension, order='F') for time in elapsed])


def redfield_generator(case):
    energies, basis = np.linalg.eigh(case['H0'])
    dimension = len(energies)
    identity = np.eye(dimension)
    gaps = energies[:, None] - energies[None, :]
    generator = np.diag(-1j * gaps.reshape(-1, order='F'))
    for coupling, bath in zip(case['a_ops'], case['baths']):
        operator = basis.conj().T @ coupling @ basis
        weighted = operator * spectrum(bath, -gaps) / 2
        contribution = (np.kron(operator.T, weighted) + np.kron(weighted.conj(), operator)
                        - np.kron(identity, operator @ weighted)
                        - np.kron((weighted.conj().T @ operator).T, identity))
        if case.get('secular', True):
            flattened = gaps.reshape(-1, order='F')
            contribution *= np.abs(flattened[:, None] - flattened[None, :]) < 1e-7
        generator += contribution
    return generator, basis


def redfield_states(case, options):
    generator, basis = redfield_generator(case)
    initial = basis.conj().T @ case['rho0'] @ basis
    states = evolve_generator(generator, initial, case['times'] - case['times'][0])
    return basis @ states @ basis.conj().T

import numpy as np
from scipy.linalg import eigh

from .baths import spectrum
from .operators import coherent_generator, dissipator, evolve_generator, frequency_sectors


def redfield_generator(case, secular=None):
    energies, basis = eigh(case['H0'])
    dimension = len(energies)
    identity = np.eye(dimension)
    generator = coherent_generator(np.diag(energies))
    frequencies = energies[None, :] - energies[:, None]
    if secular is None:
        secular = case.get('secular', False)
    for bath, laboratory_operator in zip(case['baths'], case['a_ops']):
        operator = basis.conj().T @ laboratory_operator @ basis
        if secular:
            amplitudes = []
            frequency_list = []
            for row in range(dimension):
                for column in range(dimension):
                    amplitude = np.zeros_like(operator)
                    amplitude[row, column] = operator[row, column]
                    amplitudes.append(amplitude)
                    frequency_list.append(frequencies[row, column])
            for frequency, jump in frequency_sectors(frequency_list, amplitudes):
                generator += float(spectrum(bath, frequency)) * dissipator(jump)
        else:
            weighted = 0.5 * spectrum(bath, frequencies) * operator
            generator += (np.kron(weighted, operator.T) + np.kron(operator, weighted.conj())
                          - np.kron(operator @ weighted, identity)
                          - np.kron(identity, (weighted.conj().T @ operator).T))
    return generator, basis


def propagate_redfield(case, initial, options):
    generator, basis = redfield_generator(case)
    transformed = basis.conj().T @ initial @ basis
    states = evolve_generator(generator, transformed, case['times'] - case['times'][0])
    return basis @ states @ basis.conj().T

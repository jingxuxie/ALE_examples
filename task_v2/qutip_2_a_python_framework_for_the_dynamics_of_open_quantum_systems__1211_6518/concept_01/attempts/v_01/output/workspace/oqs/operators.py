import numpy as np
from scipy.linalg import expm


def coherent_generator(hamiltonian):
    identity = np.eye(len(hamiltonian))
    return -1j * (np.kron(hamiltonian, identity) - np.kron(identity, hamiltonian.T))


def dissipator(jump):
    identity = np.eye(len(jump))
    gram = jump.conj().T @ jump
    return (np.kron(jump, jump.conj())
            - 0.5 * np.kron(gram, identity) - 0.5 * np.kron(identity, gram.T))


def frequency_sectors(frequencies, amplitudes, tolerance=1e-7):
    order = np.argsort(frequencies)
    current_frequency = None
    current_operator = None
    for index in order:
        frequency = frequencies[index]
        if current_frequency is None or frequency - current_frequency > tolerance:
            if current_operator is not None:
                yield current_frequency, current_operator
            current_frequency = frequency
            current_operator = amplitudes[index].copy()
        else:
            current_operator += amplitudes[index]
    if current_operator is not None:
        yield current_frequency, current_operator


def evolve_generator(generator, initial, delays):
    dimension = initial.shape[-1]
    vectors = initial.reshape(-1, dimension ** 2).T
    return np.asarray([(expm(generator * delay) @ vectors).T.reshape(initial.shape)
                       for delay in delays])

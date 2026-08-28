import numpy as np


def measure(case, hamiltonian, wavefunctions):
    size = len(case['hamiltonian']['real'])
    density = np.sum(abs(wavefunctions[:size]) ** 2, axis=1)
    current = []
    for destination, origin in case['current_bonds']:
        overlap = np.vdot(wavefunctions[destination], wavefunctions[origin])
        current.append(2 * np.imag(hamiltonian[destination, origin] * overlap))
    return density, np.asarray(current)

import numpy as np


def absorption(hamiltonian, interfaces, ends, config):
    result = np.zeros(hamiltonian.shape[0])
    for first, last in zip(interfaces, ends):
        start = int(first[0])
        stop = int(last[-1]) + 1
        profile = np.linspace(0, 1, stop - start)
        result[start:stop] = config['absorption'] * profile ** 4
    return result

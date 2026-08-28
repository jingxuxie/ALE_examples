import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import time
import numpy as np
from scipy.optimize import least_squares
import solver


def synthetic(qubits, seed, shots=1000000, jitter=0.0, floor=0.0, sparse=True):
    random = np.random.default_rng(seed)
    size = 1 << qubits
    rates = np.zeros(size)
    for qubit in range(qubits):
        rates[1 << qubit] = random.uniform(0.001, 0.014)
    for qubit in range(qubits - 1):
        rates[(1 << qubit) | (1 << (qubit + 1))] = random.uniform(0.0001, 0.002)
    if qubits >= 3:
        rates[7] = 0.0007
    rates[0] = -rates.sum()
    modes = np.exp(solver.hadamard(rates))
    probabilities = solver.hadamard(modes) / size
    if not sparse:
        probabilities = 0.99 * probabilities + 0.01 * random.dirichlet(np.ones(size))
        modes = solver.hadamard(probabilities)
    spam_rates = np.zeros(size)
    for qubit in range(qubits):
        spam_rates[1 << qubit] = random.uniform(0.02, 0.16)
    spam_rates[0] = -spam_rates.sum()
    spam_modes = np.exp(solver.hadamard(spam_rates))
    depths = np.array([1, 5, 10, 15, 20, 30, 45, 60, 75, 90, 105])
    rows = []
    for depth in depths:
        if jitter:
            noisy_rates = rates.copy()
            noisy_rates[1:] *= np.exp(random.normal(0, jitter, size - 1) - jitter * jitter / 2)
            noisy_rates[0] = -noisy_rates[1:].sum()
            current_modes = np.exp(solver.hadamard(noisy_rates))
        else:
            current_modes = modes
        spectrum = spam_modes * current_modes ** depth
        distribution = solver.hadamard(spectrum) / size
        distribution = (1 - floor) * distribution + floor * solver.hadamard(spam_modes) / size
        distribution = np.maximum(distribution, 0)
        distribution /= distribution.sum()
        rows.append(random.multinomial(shots, distribution))
    return np.array(rows), depths, probabilities


def evaluate(counts, depths, true):
    start = time.monotonic()
    modes, uncertainty, details = solver.fit_modes(counts, depths)
    raw = solver.hadamard(modes) / len(modes)
    projected = solver.simplex(raw)
    reconstructed = solver.reconstruct(counts, depths)
    for name, probabilities in [('raw', raw), ('simplex', projected), ('weighted', reconstructed)]:
        error = np.sum(np.abs(probabilities[1:] - true[1:])) / true[1:].sum()
        cmi_masks = np.array([[[1, 0, 0], [0, 1, 0], [0, 0, 1]]])
        print(name, 'rel_L1', round(error, 5), 'identity', round(probabilities[0], 6),
              'negative_mass', round(-probabilities[probabilities < 0].sum(), 5), end='; ')
    print('seconds', round(time.monotonic() - start, 3))
    return reconstructed


if __name__ == '__main__':
    for qubits in [3, 6, 10, 14]:
        for jitter, floor in [(0., 0.), (0.04, 0.), (0., 0.008)]:
            counts, depths, true = synthetic(qubits, 37, jitter=jitter, floor=floor)
            print('n', qubits, 'jitter', jitter, 'floor', floor, 'true identity', true[0], flush=True)
            evaluate(counts, depths, true)

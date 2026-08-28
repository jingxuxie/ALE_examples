import time
import numpy as np
from scipy.optimize import minimize
from solver import hadamard, simplex


def refine(counts, depths, initial, maxiter=250, verbose=False):
    start = time.monotonic()
    counts = np.asarray(counts, dtype=float)
    depths = np.asarray(depths, dtype=float)
    order = np.argsort(depths)
    counts, depths = counts[order], depths[order]
    times = depths - depths[0]
    size = len(initial)
    fractions = counts / counts.sum()
    rates = hadamard(initial)
    bases = np.maximum(rates[None, :], 1e-8) ** times[:, None]
    spectra = hadamard(counts / counts.sum(1, keepdims=True))
    nuisance = np.sum(bases * spectra * counts.sum(1)[:, None], axis=0) / np.maximum(np.sum(bases * bases * counts.sum(1)[:, None], axis=0), 1e-30)
    spam = simplex(hadamard(nuisance) / size)
    channel = np.maximum(initial, 1e-9)
    spam = np.maximum(spam, 1e-10)
    channel /= channel.sum()
    spam /= spam.sum()
    scale = 3.0
    vector = np.r_[np.sqrt(channel) * scale, np.sqrt(spam)]
    evaluations = [0]

    def objective(vector):
        channel_square, spam_square = vector[:size] ** 2, vector[size:] ** 2
        channel_norm, spam_norm = channel_square.sum(), spam_square.sum()
        channel, spam = channel_square / channel_norm, spam_square / spam_norm
        modes, amplitudes = hadamard(channel), hadamard(spam)
        modes = np.maximum(modes, 1e-8)
        bases = modes[None, :] ** times[:, None]
        distribution = np.maximum(hadamard(bases * amplitudes[None, :]) / size, 1e-18)
        loss = -np.sum(fractions * np.log(distribution))
        transformed = hadamard(-fractions / distribution) / size
        channel_gradient = hadamard(np.sum(transformed * bases * amplitudes[None, :] * times[:, None] / modes[None, :], axis=0))
        spam_gradient = hadamard(np.sum(transformed * bases, axis=0))
        channel_gradient = (channel_gradient - np.dot(channel_gradient, channel)) * 2 * vector[:size] / channel_norm
        spam_gradient = (spam_gradient - np.dot(spam_gradient, spam)) * 2 * vector[size:] / spam_norm
        evaluations[0] += 1
        return loss, np.r_[channel_gradient, spam_gradient]

    initial_loss = objective(vector)[0]
    fit = minimize(objective, vector, method='L-BFGS-B', jac=True, bounds=[(0, None)] * len(vector),
                   options={'maxiter': maxiter, 'ftol': 1e-13, 'gtol': 1e-9, 'maxcor': 12, 'maxls': 20})
    probabilities = fit.x[:size] ** 2
    probabilities /= probabilities.sum()
    if verbose:
        print('likelihood:', fit.message, 'iter', fit.nit, 'eval', evaluations[0],
              'loss', initial_loss, fit.fun, 'sec', time.monotonic() - start, flush=True)
    return probabilities


if __name__ == '__main__':
    import solver
    from development import synthetic
    for qubits in [3, 6, 10, 14]:
        for jitter, floor in [(0., 0.), (0.04, 0.), (0., 0.008)]:
            counts, depths, true = synthetic(qubits, 37, jitter=jitter, floor=floor)
            initial = solver.reconstruct(counts, depths)
            refined = refine(counts, depths, initial, verbose=True)
            print('n', qubits, 'jitter', jitter, 'floor', floor, 'initial',
                  np.abs(initial[1:] - true[1:]).sum()/true[1:].sum(), 'refined',
                  np.abs(refined[1:] - true[1:]).sum()/true[1:].sum(), flush=True)
    data = np.load('../participant/input/example.npz')
    initial = solver.reconstruct(data['counts'], data['depths'])
    refined = refine(data['counts'], data['depths'], initial, verbose=True)
    print('example initial', initial, 'refined', refined)

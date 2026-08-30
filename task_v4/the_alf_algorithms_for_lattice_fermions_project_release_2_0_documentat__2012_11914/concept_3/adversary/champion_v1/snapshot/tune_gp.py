import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import nnls
from models import continuum, OMEGA
from tune_nonparam import loss


def make_prior():
    random = np.random.default_rng(992)
    samples = []
    for iteration in range(12000):
        bands = random.integers(3, 6)
        weights = random.dirichlet(np.full(bands, 2.))
        mass = np.zeros(256)
        for weight in weights:
            mass += weight * continuum(random.uniform(-4.8, 4.8), random.uniform(.45, 1.5), random.uniform(-1.5, 1.5), random.uniform(.2, 1.6))[0]
        samples.append(mass)
    samples = np.array(samples)[:, np.abs(OMEGA) < 6.3]
    np.savez_compressed('gp_prior.npz', mean=samples.mean(axis=0), covariance=np.cov(samples.T))


if __name__ == '__main__':
    if not os.path.exists('gp_prior.npz'):
        make_prior()
    cache = dict(np.load('multi_cache.npz'))
    prior = dict(np.load('gp_prior.npz'))
    selected = np.abs(OMEGA) < 6.3
    eigenvalues, eigenvectors = np.linalg.eigh(prior['covariance'])
    results = {}
    for power in [.6, .8, 1.0]:
        eigen = (np.maximum(eigenvalues, 1e-12) / eigenvalues.max())**power * eigenvalues.max()
        whitening = eigenvectors.T / np.sqrt(eigen[:, None] + 1e-12)
        for strength in [.25, .5, 1, 2, 4]:
            regularizer = whitening * strength
            valuesprior = regularizer @ prior['mean']
            masses = []
            for design, target in zip(cache['design'], cache['target']):
                augmented = np.vstack((design[:, selected], regularizer, np.full((1, selected.sum()), 1e4)))
                values = np.r_[target, valuesprior, 1e4]
                coefficients = nnls(augmented, values, maxiter=3000)[0]
                mass = np.zeros(256)
                mass[selected] = coefficients / coefficients.sum()
                masses.append(mass)
            masses = np.array(masses)
            errors = loss(masses, cache['truth'], np.linspace(-8, 8, 257))
            print(power, strength, np.round(100 * np.exp(-np.array([errors[:128].mean(), errors[128:].mean()])), 3), flush=True)
            results[str(power) + '_' + str(strength)] = masses
    np.savez_compressed('gp_sweep.npz', **results)

import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
import time
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import nnls
from solve import kernel
from models import OMEGA
sys.path.insert(0, '../../participant/input')
from physics import observables, wasserstein


def loss(mass, truth, edges):
    pred = observables(mass, edges)
    actual = observables(truth, edges)
    return 22.5 * wasserstein(mass, truth, edges) / 16 + (10 / 3) * np.abs(pred['low_mass'] - actual['low_mass']) + 1.5 * np.abs(pred['band_weights'] - actual['band_weights']).sum(axis=1) / 2 + .25 * np.abs(pred['gap10'] - actual['gap10'])


def prepare():
    cache = []
    for split in ['train', 'validation']:
        data = dict(np.load('../../participant/input/' + split + '_input.npz'))
        labels = dict(np.load('../../participant/input/' + split + '_labels.npz'))
        indices = np.flatnonzero(labels['family_id'] == 5)
        if split == 'train':
            indices = indices[:128]
        for row in indices:
            response = kernel(data['beta'][row], data['tau'][row], data['omega_edges'])
            chol = np.linalg.cholesky(data['covariance'][row])
            design = solve_triangular(chol, response, lower=True)
            target = solve_triangular(chol, data['correlation'][row], lower=True)
            left, singular, right = np.linalg.svd(design, full_matrices=False)
            cache.append((singular[:24, None] * right[:24], left[:, :24].T @ target, labels['spectral_mass'][row]))
    np.savez_compressed('multi_cache.npz', design=np.array([item[0] for item in cache]), target=np.array([item[1] for item in cache]), truth=np.array([item[2] for item in cache]))


if __name__ == '__main__':
    if not os.path.exists('multi_cache.npz'):
        prepare()
    cache = dict(np.load('multi_cache.npz'))
    edges = np.linspace(-8, 8, 257)
    centers = np.linspace(-6.25, 6.25, 101)
    allresults = {}
    for width in [.15, .23, .32, .45, .6]:
        basis = np.exp(-.5 * ((OMEGA[:, None] - centers) / width)**2)
        basis[np.abs(OMEGA) > 6.3] = 0
        basis /= basis.sum(axis=0)
        for regularizer in [2, 5, 10, 20, 40, 80]:
            masses = []
            for design, target in zip(cache['design'], cache['target']):
                matrix = design @ basis
                augmented = np.vstack((matrix, regularizer * np.eye(len(centers)), np.full((1, len(centers)), 1e4)))
                values = np.r_[target, np.zeros(len(centers)), 1e4]
                coefficients = nnls(augmented, values, maxiter=3000)[0]
                mass = basis @ coefficients
                masses.append(mass / mass.sum())
            masses = np.array(masses)
            errors = loss(masses, cache['truth'], edges)
            print(width, regularizer, np.round(100 * np.exp(-np.array([errors[:128].mean(), errors[128:].mean()])), 3), flush=True)
            allresults[str(width) + '_' + str(regularizer)] = masses
    np.savez_compressed('multi_sweep.npz', **allresults)

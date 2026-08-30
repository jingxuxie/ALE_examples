from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from models import OMEGA
from multiband import fit_multi


class MultiRecovery:
    def __init__(self):
        prior = dict(np.load(Path(__file__).with_name('gp_prior.npz'), allow_pickle=False))
        eigenvalues, eigenvectors = np.linalg.eigh(prior['covariance'])
        eigen = (np.maximum(eigenvalues, 1e-12) / eigenvalues.max())**.8 * eigenvalues.max() + 1e-12
        self.regularizer = eigenvectors.T / np.sqrt(eigen[:, None])
        self.priortarget = self.regularizer @ prior['mean']
        self.covariance = (eigenvectors * eigen) @ eigenvectors.T
        self.selected = np.abs(OMEGA) < 6.3
        self.lowwindow = (np.abs(OMEGA[self.selected]) < .5).astype(float)
        self.lowcov = self.covariance @ self.lowwindow
        self.lowvariance = self.lowwindow @ self.lowcov
        centers = np.linspace(-6.25, 6.25, 101)
        self.basis = np.exp(-.5 * ((OMEGA[:, None] - centers) / .15)**2)
        self.basis[~self.selected] = 0
        self.basis /= self.basis.sum(axis=0)

    def reconstruct(self, design, target):
        matrix = design[:, self.selected]
        augmented = np.vstack((matrix, self.regularizer, np.full((1, self.selected.sum()), 1e4)))
        values = np.r_[target, self.priortarget, 1e4]
        coefficients = nnls(augmented, values, maxiter=3000)[0]
        gp_mass = np.zeros(256)
        gp_mass[self.selected] = coefficients / coefficients.sum()
        lowresponse = matrix @ self.lowcov
        posteriorvariance = self.lowvariance - lowresponse @ np.linalg.solve(np.eye(len(target)) + matrix @ self.covariance @ matrix.T, lowresponse)
        lowstd = np.sqrt(max(posteriorvariance, 1e-12))
        augmented = np.vstack((design @ self.basis, 20 * np.eye(self.basis.shape[1]), np.full((1, self.basis.shape[1]), 1e4)))
        values = np.r_[target, np.zeros(self.basis.shape[1]), 1e4]
        coefficients = nnls(augmented, values, maxiter=3000)[0]
        initialmass = self.basis @ coefficients
        initialmass /= initialmass.sum()
        prediction, masses, chis, criteria = fit_multi(design, target, initialmass, strength=4, starts=2)
        mass = .65 * prediction + .35 * gp_mass
        return mass, .35 * lowstd

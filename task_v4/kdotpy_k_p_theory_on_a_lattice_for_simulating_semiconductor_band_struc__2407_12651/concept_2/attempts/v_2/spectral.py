import numpy as np
from model import coefficients
from fast_eval import Evaluator


class SpectralEvaluator:
    def __init__(self, size=49):
        self.factors = Evaluator(size).factors

    def compute(self, parameters):
        blocks = np.array(coefficients(parameters))
        hamiltonian = np.einsum('bn,bij->nij', self.factors, blocks)
        energies, frames = np.linalg.eigh(hamiltonian)
        delta_blocks = np.empty((25, 5, 6, 6), complex)
        for index in range(25):
            direction = np.zeros(25)
            direction[index] = 1e-5
            delta_blocks[index] = (np.array(coefficients(parameters + direction)) -
                                   np.array(coefficients(parameters - direction))) / 2e-5
        delta_hamiltonian = np.einsum('bn,pbij->pnij', self.factors, delta_blocks)
        delta_energies = np.einsum('nai,pnab,nbi->pni', frames.conj(), delta_hamiltonian,
                                   frames, optimize=True).real
        gaps = energies[:, 2:5] - energies[:, 1:4]
        delta_gaps = delta_energies[:, :, 2:5] - delta_energies[:, :, 1:4]
        minimum = gaps.min(axis=0)
        weights = np.exp(-(gaps - minimum[None]) / .003)
        values = minimum - .003 * np.log(weights.sum(axis=0))
        weights /= weights.sum(axis=0)[None]
        jacobian = (delta_gaps * weights[None]).sum(axis=1).T
        return values, jacobian

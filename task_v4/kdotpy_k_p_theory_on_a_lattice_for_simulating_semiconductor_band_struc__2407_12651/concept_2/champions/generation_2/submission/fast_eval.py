import numpy as np
from model import coefficients


class Evaluator:
    def __init__(self, size=25, shift=(.137, .271)):
        self.size = size
        axis = np.arange(size)
        momenta_x, momenta_y = np.meshgrid(2 * np.pi * (axis + shift[0]) / size,
                                          2 * np.pi * (axis + shift[1]) / size, indexing='ij')
        momenta_x = momenta_x.ravel()
        momenta_y = momenta_y.ravel()
        self.factors = np.array([np.ones(size * size), np.cos(momenta_x),
                                 np.sin(momenta_x), np.cos(momenta_y), np.sin(momenta_y)])
        self.factors_x = np.array([np.zeros(size * size), -np.sin(momenta_x),
                                   np.cos(momenta_x), np.zeros(size * size), np.zeros(size * size)])
        self.factors_y = np.array([np.zeros(size * size), np.zeros(size * size),
                                   np.zeros(size * size), -np.sin(momenta_y), np.cos(momenta_y)])
        self.last_parameters = None

    def compute(self, parameters, jacobian=True):
        parameters = np.asarray(parameters)
        if (self.last_parameters is not None and np.array_equal(parameters, self.last_parameters)
                and (not jacobian or self.last_jacobian is not None)):
            return self.last_values, self.last_jacobian
        blocks = np.array(coefficients(parameters))
        hamiltonian = np.einsum('bn,bij->nij', self.factors, blocks)
        velocity_x = np.einsum('bn,bij->nij', self.factors_x, blocks)
        velocity_y = np.einsum('bn,bij->nij', self.factors_y, blocks)
        energies, frames = np.linalg.eigh(hamiltonian)
        adjoint = frames.conj().transpose(0, 2, 1)
        velocity_x = adjoint @ velocity_x @ frames
        velocity_y = adjoint @ velocity_y @ frames
        matrix_x = velocity_x[:, 0, 1:]
        matrix_y = velocity_y[:, 0, 1:]
        gaps = energies[:, 1:] - energies[:, :1]
        response = -2 * np.imag(matrix_x * matrix_y.conj()) / gaps**2
        optical = (np.abs(matrix_x)**2 + np.abs(matrix_y)**2) / gaps**2
        block_energies, block_frames = np.linalg.eigh(blocks[1:])
        norm_indices = np.argmax(np.abs(block_energies), axis=1)
        norms = np.abs(block_energies[np.arange(4), norm_indices])
        correction = 2 * np.pi * norms.sum() / 49
        gap_index = np.argmin(gaps[:, 0])
        gap_weights = np.exp(-(gaps[:, 0] - gaps[gap_index, 0]) / .01)
        smooth_gap = gaps[gap_index, 0] - .01 * np.log(gap_weights.sum())
        gap_weights /= gap_weights.sum()
        norm_index = np.unravel_index(np.argmax(np.abs(energies)), energies.shape)
        values = np.r_[response.mean(axis=0) * 2 * np.pi,
                       optical.mean(axis=0), smooth_gap - correction,
                       abs(energies[norm_index]) + correction / 2]
        derivatives = None
        if jacobian:
            delta_blocks = np.empty((25, 5, 6, 6), complex)
            for index in range(25):
                direction = np.zeros(25)
                direction[index] = 1e-5
                delta_blocks[index] = (np.array(coefficients(parameters + direction)) -
                                       np.array(coefficients(parameters - direction))) / 2e-5
            delta_hamiltonian = np.einsum('bn,pbij->pnij', self.factors, delta_blocks)
            transformed = adjoint[None] @ delta_hamiltonian @ frames[None]
            delta_energies = transformed.diagonal(axis1=-2, axis2=-1).real
            delta_gaps = delta_energies[:, :, 1:] - delta_energies[:, :, :1]
            denominators = energies[:, None, :] - energies[:, :, None]
            denominators[:, np.arange(6), np.arange(6)] = np.inf
            connection = transformed / denominators[None]
            delta_velocity_x = np.einsum('bn,pbij->pnij', self.factors_x, delta_blocks)
            delta_velocity_y = np.einsum('bn,pbij->pnij', self.factors_y, delta_blocks)
            delta_velocity_x = (adjoint[None, :, :1, :] @ delta_velocity_x @ frames[None]
                                + velocity_x[None, :, :1, :] @ connection
                                - connection[:, :, :1, :] @ velocity_x[None])
            delta_velocity_y = (adjoint[None, :, :1, :] @ delta_velocity_y @ frames[None]
                                + velocity_y[None, :, :1, :] @ connection
                                - connection[:, :, :1, :] @ velocity_y[None])
            delta_x = delta_velocity_x[:, :, 0, 1:]
            delta_y = delta_velocity_y[:, :, 0, 1:]
            delta_response = (-2 * np.imag(delta_x * matrix_y.conj()[None]
                                           + matrix_x[None] * delta_y.conj()) / gaps[None]**2
                              - 2 * response[None] * delta_gaps / gaps[None])
            delta_optical = (2 * np.real(delta_x * matrix_x.conj()[None]
                                        + delta_y * matrix_y.conj()[None]) / gaps[None]**2
                             - 2 * optical[None] * delta_gaps / gaps[None])
            norm_frames = block_frames[np.arange(4), :, norm_indices]
            delta_norms = np.einsum('bi,pbij,bj->pb', norm_frames.conj(),
                                    delta_blocks[:, 1:], norm_frames).real
            delta_norms *= np.sign(block_energies[np.arange(4), norm_indices])[None]
            delta_correction = 2 * np.pi * delta_norms.sum(axis=1) / 49
            derivatives = np.concatenate([
                delta_response.mean(axis=1) * 2 * np.pi,
                delta_optical.mean(axis=1),
                (delta_gaps[:, :, 0] @ gap_weights - delta_correction)[:, None],
                (np.sign(energies[norm_index]) * delta_energies[:, norm_index[0], norm_index[1]]
                 + delta_correction / 2)[:, None]], axis=1).T
        self.last_parameters = parameters.copy()
        self.last_values = values
        self.last_jacobian = derivatives
        return values, derivatives


if __name__ == '__main__':
    import time
    from optimize import BASE
    from model import diagnose
    evaluator = Evaluator()
    began = time.time()
    values, jacobian = evaluator.compute(BASE)
    print('analytic time', time.time() - began)
    finite = []
    began = time.time()
    for index in range(25):
        direction = np.zeros(25)
        direction[index] = 1e-5
        finite.append((evaluator.compute(BASE + direction, False)[0] -
                       evaluator.compute(BASE - direction, False)[0]) / 2e-5)
    finite = np.array(finite).T
    print('finite time', time.time() - began)
    print('max error', np.max(np.abs(finite - jacobian)),
          'per metric', np.max(np.abs(finite - jacobian), axis=1))
    print(values)
    print(diagnose(BASE, 25))

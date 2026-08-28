import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import functools
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, eigsh, splu


@functools.lru_cache(maxsize=8)
def reflection_basis(nx, ny, antiperiodic):
    indices = np.arange(4 * nx * ny)
    components = indices % 4
    rows = (indices // 4) % ny
    columns = indices // (4 * ny)
    partners = (((-columns) % nx) * ny + rows) * 4 + ((components + 2) % 4)
    selected = indices < partners
    primary = indices[selected]
    secondary = partners[selected]
    dimension = len(primary)
    signs = np.where(antiperiodic & (columns[selected] != 0), -1.0, 1.0)
    return sparse.csc_matrix((np.concatenate((np.ones(dimension), signs)) / np.sqrt(2),
                             (np.concatenate((primary, secondary)), np.tile(np.arange(dimension), 2))),
                            shape=(len(indices), dimension))


def permutation_sign(permutation):
    visited = np.zeros(len(permutation), dtype=bool)
    cycles = 0
    for start in range(len(permutation)):
        if visited[start]:
            continue
        cycles += 1
        current = start
        while not visited[current]:
            visited[current] = True
            current = permutation[current]
    return -1 if (len(permutation) - cycles) % 2 else 1


def factorize(matrix, stable=False):
    return splu(matrix, permc_spec='COLAMD' if stable else 'MMD_AT_PLUS_A',
                diag_pivot_thresh=1.0 if stable else 0.0)


def determinant_sign(factor):
    diagonal = factor.U.diagonal()
    phase = np.prod(diagonal / np.abs(diagonal))
    phase *= permutation_sign(factor.perm_r) * permutation_sign(factor.perm_c)
    if abs(phase.imag) > 1e-4:
        raise ArithmeticError('Unresolved Hermitian determinant')
    return -1 if phase.real < 0 else 1


def nearest(matrix, factor=None, bands=2, tolerance=2e-6):
    if factor is None:
        factor = factorize(matrix)
    inverse = LinearOperator(matrix.shape, matvec=factor.solve, dtype=complex)
    initial = np.random.RandomState(17).normal(size=matrix.shape[0])
    energies, vectors = eigsh(matrix, k=bands, sigma=0.0, which='LM', OPinv=inverse,
                             tol=tolerance, ncv=max(12, 2 * bands + 2), maxiter=500, v0=initial)
    error = np.max(np.linalg.norm(matrix @ vectors - vectors * energies, axis=0))
    if not np.all(np.isfinite(energies)) or error > 1e-6:
        inverse = LinearOperator(matrix.shape, matvec=factorize(matrix, True).solve, dtype=complex)
        energies, vectors = eigsh(matrix, k=max(4, bands), sigma=0.0, which='LM', OPinv=inverse,
                                 tol=1e-9, maxiter=2000, v0=initial)
        error = np.max(np.linalg.norm(matrix @ vectors - vectors * energies, axis=0))
        if not np.all(np.isfinite(energies)) or error > 2e-5:
            raise ArithmeticError('Unreliable low-energy solve')
    return float(np.min(np.abs(energies)))


class Spectrum:
    def __init__(self, model):
        self.model = model
        self.values = {}
        self.signs = {}

    def endpoint(self, antiperiodic, with_gap=True):
        momentum = float(np.pi if antiperiodic else 0.0)
        if antiperiodic in self.signs and (not with_gap or momentum in self.values):
            return self.signs[antiperiodic]
        basis = reflection_basis(self.model.nx, self.model.ny, antiperiodic)
        matrix = (basis.T @ self.model.hamiltonian(momentum) @ basis).tocsc()
        matrix.eliminate_zeros()
        factor = factorize(matrix, stable=not with_gap)
        try:
            sign = determinant_sign(factor)
        except ArithmeticError:
            factor = factorize(matrix, True)
            sign = determinant_sign(factor)
        self.signs[antiperiodic] = sign
        if with_gap:
            self.values[momentum] = nearest(matrix, factor)
        return sign

    def invariant(self, with_gap=False):
        return self.endpoint(False, with_gap) * self.endpoint(True, with_gap)

    def gap(self, momentum):
        momentum = float(momentum)
        if momentum not in self.values:
            if abs(momentum) < 1e-12:
                self.endpoint(False)
            elif abs(momentum - np.pi) < 1e-12:
                self.endpoint(True)
            else:
                self.values[momentum] = nearest(self.model.hamiltonian(momentum))
        return self.values[momentum]

    def scan(self, count=5):
        for momentum in np.linspace(0, np.pi, count):
            self.gap(momentum)
        return min(self.values.values())

    def refine(self):
        momenta = sorted(self.values)
        values = np.array([self.values[momentum] for momentum in momenta])
        minimum = int(np.argmin(values))
        center = momenta[minimum]
        if 0 < minimum < len(momenta) - 1:
            neighborhood = np.array(momenta[minimum - 1:minimum + 2])
            coefficients = np.polyfit(neighborhood - center, values[minimum - 1:minimum + 2] ** 2, 2)
            if coefficients[0] > 0:
                center += float(np.clip(-coefficients[1] / (2 * coefficients[0]),
                                        neighborhood[0] - center, neighborhood[-1] - center))
        index = int(round(center * 50 / np.pi))
        for sample in range(max(0, index - 1), min(50, index + 1) + 1):
            self.gap(sample * np.pi / 50)
        return min(self.values.values())

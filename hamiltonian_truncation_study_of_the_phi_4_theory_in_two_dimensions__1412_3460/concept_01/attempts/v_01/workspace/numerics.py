import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh


def diagonalize(matrix, count=3, vectors=False):
    count = min(count, matrix.shape[0])
    asymmetry = matrix - matrix.T
    if np.max(abs(asymmetry.data), initial=0) > 1e-9:
        raise ValueError('Unpaired non-Hermitian Hamiltonian')
    if matrix.shape[0] < max(220, 3 * count):
        values, eigenvectors = linalg.eigh(matrix.toarray(), subset_by_index=(0, count - 1), driver='evr')
    else:
        initial = np.random.default_rng(19381).normal(size=matrix.shape[0])
        values, eigenvectors = eigsh(matrix, k=count, which='SA', tol=2e-10, v0=initial,
                                    ncv=max(32, 2 * count + 8), maxiter=20000)
        permutation = np.argsort(values)
        values, eigenvectors = values[permutation], eigenvectors[:, permutation]
    residual = np.max(np.linalg.norm(matrix @ eigenvectors - eigenvectors * values, axis=0))
    if residual > 2e-7:
        raise ArithmeticError(f'Eigensolver residual {residual}')
    return (values, eigenvectors, residual) if vectors else values


def hamiltonian(sector, coefficients, constant=0.0):
    result = sparse.diags(sector['energy'] + constant, format='csr')
    for key, value in coefficients.items():
        if key not in sector['operators']:
            raise ValueError(f'Missing required operator {key}')
        result += value * sector['operators'][key]
    return result

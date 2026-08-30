"""Private baseline-equivalent pair solver with explicitly ordered contractions."""

import numpy as np
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh


def _apply_pair(left, left_mpo, right_mpo, right, theta):
    temporary = np.einsum("awb,bqsf->awqsf", left, theta, optimize=True)
    temporary = np.einsum("awqsf,wxpq->axpsf", temporary, left_mpo, optimize=True)
    temporary = np.einsum("axpsf,xyrs->ayprf", temporary, right_mpo, optimize=True)
    return np.einsum("ayprf,cyf->aprc", temporary, right, optimize=True)


def optimize_pair(first, second, left, right, left_mpo, right_mpo, cap, direction,
                  tolerance, maxiter):
    theta = np.tensordot(first, second, axes=(2, 0))
    shape = theta.shape

    def matvec(vector):
        return _apply_pair(left, left_mpo, right_mpo, right, vector.reshape(shape)).ravel()

    operator = LinearOperator((theta.size, theta.size), matvec=matvec, dtype=theta.dtype)
    starting = theta.ravel() / np.linalg.norm(theta)
    try:
        _, vectors = eigsh(operator, k=1, which="SA", v0=starting, tol=tolerance,
                           maxiter=maxiter, ncv=min(20, theta.size))
        vector = vectors[:, 0]
    except ArpackNoConvergence as error:
        vector = error.eigenvectors[:, 0] if error.eigenvectors.shape[1] else starting
    matrix = vector.reshape(shape[0] * shape[1], shape[2] * shape[3])
    left_vectors, values, right_vectors = np.linalg.svd(matrix, full_matrices=False)
    rank = min(cap, len(values))
    left_vectors = left_vectors[:, :rank]
    right_vectors = right_vectors[:rank]
    values = values[:rank]
    values /= np.linalg.norm(values)
    if direction == "right":
        return (left_vectors.reshape(shape[0], shape[1], rank),
                (values[:, None] * right_vectors).reshape(rank, shape[2], shape[3]))
    return ((left_vectors * values).reshape(shape[0], shape[1], rank),
            right_vectors.reshape(rank, shape[2], shape[3]))


def install():
    """Replace only the already-imported baseline engine's pair optimizer."""
    import mps

    mps.optimize_pair = optimize_pair

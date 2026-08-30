"""Editable small two-site variational engine; no tensor-network dependency."""

import time

import numpy as np
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh

from contractor import canonicalize, hamiltonian_terms


def make_mpo(request, parity_bias=0.0):
    onsite, positions = hamiltonian_terms(request)
    dimension = request["local_dim"]
    length = request["n_sites"]
    width = 4 if parity_bias else 3
    identity = np.eye(dimension)
    parity = np.diag((-1.0) ** np.arange(dimension))
    result = []
    for site in range(length):
        tensor = np.zeros((width, width, dimension, dimension))
        tensor[0, 0] = identity
        tensor[0, 2] = onsite[site]
        tensor[2, 2] = identity
        if site + 1 < length:
            tensor[0, 1] = -request["coupling"][site] * positions[site]
        tensor[1, 2] = positions[site]
        if parity_bias:
            if site == 0:
                tensor[0, 3] = -parity_bias * parity
            elif site == length - 1:
                tensor[3, 2] = parity
            else:
                tensor[3, 3] = parity
        if site == 0:
            tensor = tensor[0:1]
        if site == length - 1:
            tensor = tensor[:, 2:3]
        result.append(tensor)
    return result


def product_state(request, tilt=0.0, odd_site=None):
    onsite, positions = hamiltonian_terms(request)
    tensors = []
    for site, local in enumerate(onsite):
        matrix = local - tilt * positions[site]
        if tilt == 0 and request["field"][site] == 0:
            indices = np.arange(1 if site == odd_site else 0, request["local_dim"], 2)
            _, eigenvectors = np.linalg.eigh(matrix[np.ix_(indices, indices)])
            vector = np.zeros(request["local_dim"])
            vector[indices] = eigenvectors[:, 0]
        else:
            _, eigenvectors = np.linalg.eigh(matrix)
            vector = eigenvectors[:, 0]
        tensors.append(vector.reshape(1, -1, 1))
    return tensors


def project_parity(tensors, sector):
    if sector == "any":
        return canonicalize(tensors)
    sign = 1.0 if sector == "even" else -1.0
    parity = (-1.0) ** np.arange(tensors[0].shape[1])
    result = []
    for site, tensor in enumerate(tensors):
        reflected = tensor * parity[None, :, None]
        if site == 0:
            result.append(np.concatenate((tensor, sign * reflected), axis=2))
        elif site == len(tensors) - 1:
            result.append(np.concatenate((tensor, reflected), axis=0))
        else:
            left, physical, right = tensor.shape
            combined = np.zeros((2 * left, physical, 2 * right), dtype=tensor.dtype)
            combined[:left, :, :right] = tensor
            combined[left:, :, right:] = reflected
            result.append(combined)
    return canonicalize(result)


def right_canonical(tensors):
    result = [tensor.copy() for tensor in tensors]
    for site in range(len(result) - 1, 0, -1):
        left, physical, right = result[site].shape
        orthogonal, triangular = np.linalg.qr(result[site].reshape(left, physical * right).T)
        result[site] = orthogonal.T.reshape(orthogonal.shape[1], physical, right)
        result[site - 1] = np.tensordot(result[site - 1], triangular.T, axes=(2, 0))
    result[0] /= np.linalg.norm(result[0])
    return result


def left_step(environment, tensor, operator):
    return np.einsum("awb,apr,wxpq,bqs->rxs", environment, tensor.conj(), operator,
                     tensor, optimize=True)


def right_step(environment, tensor, operator):
    return np.einsum("apr,wxpq,bqs,rxs->awb", tensor.conj(), operator, tensor,
                     environment, optimize=True)


def optimize_pair(first, second, left, right, left_mpo, right_mpo, cap, direction,
                  tolerance, maxiter):
    theta = np.tensordot(first, second, axes=(2, 0))
    shape = theta.shape
    dummy = np.zeros(shape)
    expression = "awb,wxpq,xyrs,cyf,bqsf->aprc"
    path = np.einsum_path(expression, left, left_mpo, right_mpo, right, dummy,
                          optimize="greedy")[0]

    def matvec(vector):
        return np.einsum(expression, left, left_mpo, right_mpo, right,
                         vector.reshape(shape), optimize=path).ravel()

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


def sweep(tensors, mpo, cap, tolerance=1e-5, maxiter=40, deadline=float("inf")):
    tensors = right_canonical(tensors)
    length = len(tensors)
    right_environments = [None] * (length + 1)
    right_environments[length] = np.ones((1, 1, 1))
    for site in range(length - 1, -1, -1):
        right_environments[site] = right_step(right_environments[site + 1],
                                              tensors[site], mpo[site])
    left_environments = [np.ones((1, 1, 1))]
    for site in range(length - 1):
        if time.process_time() >= deadline:
            return tensors
        tensors[site], tensors[site + 1] = optimize_pair(
            tensors[site], tensors[site + 1], left_environments[site],
            right_environments[site + 2], mpo[site], mpo[site + 1], cap, "right",
            tolerance, maxiter)
        left_environments.append(left_step(left_environments[site], tensors[site], mpo[site]))
    environment = np.ones((1, 1, 1))
    for site in range(length - 2, -1, -1):
        if time.process_time() >= deadline:
            return tensors
        tensors[site], tensors[site + 1] = optimize_pair(
            tensors[site], tensors[site + 1], left_environments[site], environment,
            mpo[site], mpo[site + 1], cap, "left", tolerance, maxiter)
        environment = right_step(environment, tensors[site + 1], mpo[site + 1])
    return tensors

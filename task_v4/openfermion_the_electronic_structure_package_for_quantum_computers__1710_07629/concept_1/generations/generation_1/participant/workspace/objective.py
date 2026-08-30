import numpy as np


def transformed(case, orbital, auxiliary):
    one_body = np.asarray(case["one_body"], dtype=float)
    factors = np.asarray(case["factors"], dtype=float)
    rotated = np.einsum("pi,apq,qj->aij", orbital, factors, orbital, optimize=True)
    mixed = np.einsum("ab,bij->aij", auxiliary, rotated, optimize=True)
    return orbital.T @ one_body @ orbital, mixed


def cost(case, orbital, auxiliary):
    one_body, factors = transformed(case, orbital, auxiliary)
    weights = np.sum(np.abs(factors), axis=(1, 2))
    return float(np.abs(one_body).sum() + 0.5 * weights @ weights)


def validate(case, solution):
    dimension = len(case["one_body"])
    rank = len(case["factors"])
    orbital = np.asarray(solution["orbital"], dtype=float)
    auxiliary = np.asarray(solution["auxiliary"], dtype=float)
    if orbital.shape != (dimension, dimension) or auxiliary.shape != (rank, rank):
        raise ValueError("incorrect transformation dimensions")
    if not np.isfinite(orbital).all() or not np.isfinite(auxiliary).all():
        raise ValueError("nonfinite transformation")
    for matrix in (orbital, auxiliary):
        if np.linalg.norm(matrix.T @ matrix - np.eye(len(matrix)), ord="fro") > 1e-7:
            raise ValueError("transformation is not orthogonal")
    return cost(case, orbital, auxiliary)

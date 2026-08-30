import numpy as np
from scipy.linalg import cho_factor, cho_solve


def bounded_fit(matrix, target, initial=None, ridge=1e-8, max_iter=50, reference=None):
    dimension = matrix.shape[1]
    hessian = matrix.T @ matrix
    diagonal = np.diag_indices(dimension)
    hessian[diagonal] += ridge
    gradient = matrix.T @ target
    if reference is not None:
        gradient += ridge * reference
    if initial is None:
        values = np.full(dimension, .2)
    else:
        values = np.maximum(initial, .001)
    dual = np.maximum(hessian @ values - gradient, .001)
    for iteration in range(max_iter):
        residual = hessian @ values - gradient - dual
        product = values * dual
        gap = np.mean(product)
        if gap < 1e-12 and np.max(np.abs(residual)) < 1e-9:
            break
        augmented = hessian.copy()
        augmented[diagonal] += dual / values
        factor = cho_factor(augmented, check_finite=False)
        affine_values = cho_solve(factor, -residual - dual, check_finite=False)
        affine_dual = -dual - (dual / values) * affine_values
        primal_negative = affine_values < 0
        dual_negative = affine_dual < 0
        primal_step = min(1., np.min(-values[primal_negative] / affine_values[primal_negative], initial=1.))
        dual_step = min(1., np.min(-dual[dual_negative] / affine_dual[dual_negative], initial=1.))
        affine_gap = np.mean((values + primal_step * affine_values) * (dual + dual_step * affine_dual))
        centering = min(1., (affine_gap / gap)**3)
        correction = centering * gap - affine_values * affine_dual
        delta_values = cho_solve(factor, -residual - dual + correction / values, check_finite=False)
        delta_dual = -dual + correction / values - (dual / values) * delta_values
        primal_negative = delta_values < 0
        dual_negative = delta_dual < 0
        primal_step = min(1., .995 * np.min(-values[primal_negative] / delta_values[primal_negative], initial=np.inf))
        dual_step = min(1., .995 * np.min(-dual[dual_negative] / delta_dual[dual_negative], initial=np.inf))
        values += primal_step * delta_values
        dual += dual_step * delta_dual
    return values

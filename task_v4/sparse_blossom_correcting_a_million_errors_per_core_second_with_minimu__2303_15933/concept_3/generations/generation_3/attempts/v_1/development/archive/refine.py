import time
import sys
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from solution_v2 import LIB, contiguous


def refine(model, point, width=10, hashbits=14, ridge=0.01):
    started = time.process_time()
    channels = model.channels
    rates = np.exp(point)
    blocks = model.blocks(width)
    work = []
    offset = 0
    for codes in blocks:
        mask = sum(1 << int(detector) for detector in np.flatnonzero(codes))
        selected = np.flatnonzero((model.unions & mask) == model.unions)
        work.append((codes, selected, slice(offset, offset + len(selected))))
        offset += len(selected)
    score_sum = np.zeros(offset)
    sensitivity = np.zeros((offset, channels))
    covariance = np.zeros((offset, offset))
    information = np.zeros((channels, channels))
    gradient = np.zeros(channels)
    for action in np.flatnonzero(model.spent):
        syndromes = np.concatenate([item[0] for item in model.raw[action]])
        multiplicities = np.concatenate([item[1] for item in model.raw[action]])
        unique, inverse = np.unique(syndromes, return_inverse=True)
        counts = np.bincount(inverse, weights=multiplicities)
        shots = counts.sum()
        if action in model.rare_actions:
            codes = model.hash_codes & ((1 << hashbits) - 1)
            size, active, masks, exposures, weights, alternate, unused, scale = model.make_block(codes, np.array([action]), observed=False)
            probability = np.zeros((1, size))
            jacobian = np.zeros((1, len(active), size))
            LIB.distribution(size, len(active), 1, masks, exposures, weights, alternate,
                             contiguous(rates[active]), probability, jacobian)
            probability = np.maximum(probability[0], 1e-20)
            jacobian = jacobian[0]
            normalized = jacobian / np.sqrt(probability)
            information[np.ix_(active, active)] += shots * (normalized @ normalized.T)
            projected = model.project(unique, codes)
            gradient[active] -= (jacobian[:, projected] / probability[projected]) @ counts
        else:
            scores = np.zeros((offset, len(unique)))
            for codes, selected, rows in work:
                size, active, masks, exposures, weights, alternate, unused, scale = model.make_block(codes, np.array([action]), observed=False)
                probability = np.zeros((1, size))
                jacobian = np.zeros((1, len(active), size))
                LIB.distribution(size, len(active), 1, masks, exposures, weights, alternate,
                                 contiguous(rates[active]), probability, jacobian)
                probability = np.maximum(probability[0], 1e-20)
                jacobian = jacobian[0]
                positions = np.searchsorted(active, selected)
                jacobian_selected = jacobian[positions]
                sensitivity[rows, active] += shots * ((jacobian_selected / probability) @ jacobian.T)
                projected = model.project(unique, codes)
                scores[rows] = -jacobian_selected[:, projected] / probability[projected]
            mean = scores @ counts
            score_sum += mean
            normalized = scores * np.sqrt(counts)
            covariance += normalized @ normalized.T - np.outer(mean, mean) / shots
    deviations = np.sqrt(np.maximum(np.diag(covariance), 1e-12))
    covariance /= deviations[:, None] * deviations[None]
    covariance = (1-ridge)*covariance + ridge*np.eye(offset)
    sensitivity /= deviations[:, None]
    score_sum /= deviations
    factor = cho_factor(covariance, lower=True, check_finite=False)
    transformed = cho_solve(factor, sensitivity, check_finite=False)
    information += sensitivity.T @ transformed
    gradient += transformed.T @ score_sum
    inverse = np.linalg.inv(information + np.eye(channels) * 1e-7)
    center = point - inverse @ gradient
    bounds = model.bounds - point[:, None]
    def objective(displacement):
        transformed = information @ displacement
        return gradient @ displacement + 0.5 * displacement @ transformed, gradient + transformed
    fitted = minimize(objective, np.zeros(channels), jac=True, method='L-BFGS-B', bounds=bounds,
                      options={'maxiter': 100, 'ftol': 1e-12, 'gtol': 1e-5})
    print('refine', width, offset, 'cpu', time.process_time()-started, 'shift', np.sqrt(np.mean(fitted.x**2)), file=sys.stderr, flush=True)
    return point + fitted.x, center, inverse

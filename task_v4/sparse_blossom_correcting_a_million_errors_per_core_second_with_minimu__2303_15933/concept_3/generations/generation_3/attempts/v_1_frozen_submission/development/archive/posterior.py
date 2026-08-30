import sys
import time
import numpy as np
from scipy.special import ndtr, ndtri, logsumexp
from scipy.stats import qmc


def truncated_mean(center, covariance, bounds):
    deviations = np.sqrt(np.maximum(np.diag(covariance), 1e-12))
    distances = np.minimum(center - bounds[:, 0], bounds[:, 1] - center) / deviations
    order = np.argsort(distances)
    factor = np.linalg.cholesky(covariance[order][:, order])
    bounds = bounds[order]
    ordered_center = center[order]
    uniform = qmc.Sobol(len(center), scramble=True, seed=871923).random_base2(12)
    latent = np.zeros_like(uniform)
    log_weights = np.zeros(len(uniform))
    for channel in range(len(center)):
        conditional = ordered_center[channel] + latent[:, :channel] @ factor[channel, :channel]
        lower = (bounds[channel, 0] - conditional) / factor[channel, channel]
        upper = (bounds[channel, 1] - conditional) / factor[channel, channel]
        positive = lower > 0
        first = ndtr(np.where(positive, -upper, lower))
        second = ndtr(np.where(positive, -lower, upper))
        mass = np.maximum(second - first, 1e-300)
        quantile = np.clip(first + uniform[:, channel] * mass, 1e-300, 1 - np.finfo(float).eps)
        latent[:, channel] = np.where(positive, -ndtri(quantile), ndtri(quantile))
        log_weights += np.log(mass)
    points = ordered_center[None] + latent @ factor.T
    weights = np.exp(log_weights - logsumexp(log_weights))
    mean = (weights @ points)[np.argsort(order)]
    return mean


def apply(model, point, width=12, hashbits=15):
    started = time.process_time()
    fisher = model.fisher(point, width=10)
    information = np.einsum('a,akl->kl', model.spent, fisher)
    covariance = np.linalg.inv(information + np.eye(model.channels) * 1e-6)
    unused, gradient = model.evaluate(point, model.setup(width, hashbits))
    center = point - covariance @ gradient
    result = truncated_mean(center, covariance, model.bounds)
    print('posterior', time.process_time()-started, file=sys.stderr, flush=True)
    return result

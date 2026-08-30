import numpy as np
from scipy.special import ndtr, ndtri
from scipy.stats import qmc


def log_likelihoods(model, counts, samples, batch_size=16):
    from solution import walsh
    selected = np.flatnonzero(counts.sum(axis=1))
    observed = counts[selected]
    exposures = model.exposures[selected]
    odd = model.odd[selected]
    weights = model.weights[selected]
    likelihoods = np.empty(len(samples))
    for start in range(0, len(samples), batch_size):
        batch = samples[start:start + batch_size]
        attenuation = np.exp(-2 * exposures[None, :, :, :] * np.exp(batch)[:, None, None, :])
        products = np.ones((len(batch), len(selected), 2, model.state_count))
        for channel in range(len(model.bounds)):
            parity = odd[None, :, None, channel, :]
            products *= 1 - parity + attenuation[:, :, :, channel, None] * parity
        probability = np.maximum(walsh(np.sum(products * weights[None, :, :, None], axis=2))
                                 / model.state_count, 1e-15)
        likelihoods[start:start + len(batch)] = np.einsum('bas,as->b', np.log(probability), observed)
    return likelihoods


def posterior_mean(model, counts, fitted, power=10):
    bounds = model.bounds.copy()
    model.bounds = bounds + np.array([-0.5, 0.5])
    mode = model.fit(counts, fitted, iterations=70)
    model.bounds = bounds
    information = np.einsum('a,akl->kl', counts.sum(axis=1), model.fisher(mode))
    covariance = np.linalg.inv(information)
    cholesky = np.linalg.cholesky(covariance)
    dimension = len(mode)
    uniforms = qmc.Sobol(dimension, scramble=True, seed=783).random_base2(power)
    white = np.zeros_like(uniforms)
    log_mass = np.zeros(len(uniforms))
    for channel in range(dimension):
        center = mode[channel] + white[:, :channel] @ cholesky[channel, :channel]
        low = ndtr((bounds[channel, 0] - center) / cholesky[channel, channel])
        high = ndtr((bounds[channel, 1] - center) / cholesky[channel, channel])
        mass = np.maximum(high - low, 1e-100)
        white[:, channel] = ndtri(np.clip(low + uniforms[:, channel] * mass, 1e-15, 1 - 1e-15))
        log_mass += np.log(mass)
    samples = mode + white @ cholesky.T
    log_weights = log_mass + 0.5 * np.sum(white ** 2, axis=1)
    log_weights += log_likelihoods(model, counts, samples)
    weights = np.exp(log_weights - log_weights.max())
    weights /= weights.sum()
    estimate = weights @ samples
    return estimate, 1 / np.sum(weights ** 2)

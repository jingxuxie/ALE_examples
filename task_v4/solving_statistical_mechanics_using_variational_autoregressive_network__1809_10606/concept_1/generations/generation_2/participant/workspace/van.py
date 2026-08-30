import numpy as np
from scipy.special import expit, logsumexp


def configurations(count):
    indices = np.arange(1 << count, dtype=np.uint32)
    return (2 * ((indices[:, None] >> np.arange(count)) & 1).astype(np.int8) - 1)


def energy(spins, couplings, fields):
    return -0.5 * np.einsum("bi,ij,bj->b", spins, couplings, spins, optimize=True) - spins @ fields


def log_probability(spins, model):
    weights = np.asarray(model["weights"], dtype=float)
    biases = np.asarray(model["biases"], dtype=float)
    logs = [-np.logaddexp(0, -spins * (spins @ matrix.T + bias)).sum(axis=1)
            for matrix, bias in zip(weights, biases)]
    return logsumexp(np.stack(logs, axis=1) + np.log(model["mixing"]), axis=1)


def sample_component(rng, weights, biases, order, draws):
    spins = np.zeros((draws, len(biases)))
    for site in order:
        probability = expit(spins @ weights[site] + biases[site])
        spins[:, site] = 2 * (rng.random(draws) < probability) - 1
    return spins


def exact_metrics(instance, model):
    spins = configurations(instance["n"]).astype(float)
    log_unnormalized = -energy(spins, np.asarray(instance["couplings"]), np.asarray(instance["fields"]))
    log_target = log_unnormalized - logsumexp(log_unnormalized)
    log_model = log_probability(spins, model)
    return {"kl": float(np.exp(log_model) @ (log_model - log_target)),
            "ess": float(np.exp(-logsumexp(2 * log_target - log_model))),
            "normalization": float(np.exp(logsumexp(log_model)))}

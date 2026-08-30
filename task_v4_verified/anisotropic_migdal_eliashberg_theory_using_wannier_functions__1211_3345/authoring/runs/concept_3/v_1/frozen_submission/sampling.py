import time
import numpy as np
from scipy.special import ndtr, ndtri
from model import Fit, whiten


def initialize_chains(center, covariance, initial, count, random, sweeps=60):
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    transform = eigenvectors * np.sqrt(np.maximum(eigenvalues, 1e-12))
    coordinates = np.broadcast_to(np.linalg.solve(transform, initial - center), (count, len(center))).copy()
    positions = np.broadcast_to(initial, (count, len(center))).copy()
    for sweep in range(sweeps):
        for axis in range(len(center)):
            direction = transform[:, axis]
            without = positions - coordinates[:, axis, None] * direction
            edge_zero = np.full_like(without, -np.inf)
            edge_one = np.full_like(without, np.inf)
            nonzero = np.abs(direction) > 1e-15
            np.divide(-without, direction, out=edge_zero, where=nonzero)
            np.divide(1 - without, direction, out=edge_one, where=nonzero)
            lower = np.max(np.minimum(edge_zero, edge_one), axis=1)
            upper = np.min(np.maximum(edge_zero, edge_one), axis=1)
            reflected = lower > 0
            low_cdf = ndtr(np.where(reflected, -upper, lower))
            high_cdf = ndtr(np.where(reflected, -lower, upper))
            quantile = low_cdf + random.uniform(size=count) * np.maximum(high_cdf - low_cdf, 0)
            coordinate = ndtri(np.clip(quantile, 1e-300, 1 - 1e-15))
            coordinate = np.where(reflected, -coordinate, coordinate)
            coordinate = np.clip(coordinate, lower, upper)
            positions = without + coordinate[:, None] * direction
            coordinates[:, axis] = coordinate
    return np.clip(positions, 0, 1)


def posterior_mass(physics, target_physics, observed, sigma, family, parameters, fit, seed, budget=3., chains=32, steps=400):
    started = time.process_time()
    fitter = Fit(physics, observed, sigma, family, 3.)
    active = fitter.active
    covariance = np.linalg.inv(fit.jac.T @ fit.jac)
    center = parameters[active] - covariance @ (fit.jac.T @ fit.fun)
    random = np.random.default_rng(seed)
    samples = initialize_chains(center, covariance, parameters[active], chains, random)
    latent = np.broadcast_to(parameters, (chains, 32)).copy()
    latent[:, active] = samples

    def log_probability(position):
        residual = whiten(physics.forward(position, family, False) - observed, sigma)
        return -.5 * np.sum(residual ** 2)

    logprobs = np.array([log_probability(position) for position in latent])
    factor = np.linalg.cholesky(covariance)
    scale = 2.38 / np.sqrt(2 * len(active))
    saved = []
    for step in range(steps):
        for chain in range(chains):
            proposal = latent[chain].copy()
            if random.uniform() < .2:
                proposal[active] += scale * np.sqrt(2) * (factor @ random.normal(size=len(active)))
            else:
                first = int(random.integers(chains - 1))
                first += first >= chain
                second = int(random.integers(chains - 2))
                second += second >= min(first, chain)
                second += second >= max(first, chain)
                proposal[active] += scale * (latent[first, active] - latent[second, active]) + 1e-5 * random.normal(size=len(active))
            if np.any(proposal[active] < 0) or np.any(proposal[active] > 1):
                continue
            proposed_logprob = log_probability(proposal)
            if np.log(random.uniform()) < proposed_logprob - logprobs[chain]:
                latent[chain] = proposal
                logprobs[chain] = proposed_logprob
        if step >= 120 and step % 40 == 0:
            saved.append(latent.copy())
        if step >= 120 and step % 20 == 0 and time.process_time() - started > budget - .12:
            break
    if not saved:
        saved.append(latent.copy())
    draws = np.concatenate(saved[-5:], axis=0)
    return np.mean([target_physics.target(position, family) for position in draws], axis=0)

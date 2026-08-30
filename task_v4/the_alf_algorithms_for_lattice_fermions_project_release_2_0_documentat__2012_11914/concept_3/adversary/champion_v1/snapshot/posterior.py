import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import time
import numpy as np
from multiband import fit_multi, spectrum_multi
from models import OMEGA
from tune_nonparam import loss


def mass_only(parameters, bands):
    centers = -4.8 + 9.6 * parameters[:bands]
    widths = .45 + 1.05 * parameters[bands:2 * bands]
    skews = -1.5 + 3 * parameters[2 * bands:3 * bands]
    shapes = .2 + 1.4 * parameters[3 * bands:4 * bands]
    logits = np.r_[6 * (parameters[4 * bands:] - .5), 0.]
    weights = np.exp(logits - logits.max())
    weights /= weights.sum()
    scaled = (OMEGA[:, None] - centers) / widths
    base = np.maximum(1 - scaled**2, 0)
    profile = base**shapes * np.exp(skews * np.clip(scaled, -1, 1))
    return (profile / profile.sum(axis=0)) @ weights, 2 * np.log(weights).sum()


def sample_posterior(design, target, initial, bands, random, iterations=5000, burnin=1000):
    parameters = initial.copy()
    mass, derivative = spectrum_multi(parameters, bands)
    jacobian = design @ derivative
    covariance = np.linalg.inv(jacobian.T @ jacobian + 12 * np.eye(len(parameters)))
    proposal = np.linalg.cholesky(covariance)
    mass, logprior = mass_only(parameters, bands)
    residual = design @ mass - target
    current = -.5 * (residual @ residual) + logprior
    scale = 2.38 / np.sqrt(len(parameters))
    spectra = []
    accepted = 0
    totalaccepted = 0
    for iteration in range(iterations):
        candidate = parameters + scale * (proposal @ random.normal(size=len(parameters)))
        if np.min(candidate) >= 0 and np.max(candidate) <= 1:
            candidate_mass, logprior = mass_only(candidate, bands)
            residual = design @ candidate_mass - target
            value = -.5 * (residual @ residual) + logprior
            if np.log(random.random()) < value - current:
                parameters = candidate
                current = value
                mass = candidate_mass
                accepted += 1
                totalaccepted += 1
        if iteration < burnin and (iteration + 1) % 100 == 0:
            scale *= np.exp((accepted / 100 - .23) * 1.5)
            accepted = 0
        if iteration >= burnin and iteration % 20 == 0:
            spectra.append(mass.copy())
    return np.array(spectra), totalaccepted / iterations


if __name__ == '__main__':
    cache = dict(np.load('multi_cache.npz'))
    initial = dict(np.load('multi_sweep.npz'))['0.15_20']
    random = np.random.default_rng(9521)
    started = time.monotonic()
    means, medians, mapmass, allsamples, accepts = [], [], [], [], []
    for row, (design, target) in enumerate(zip(cache['design'], cache['target'])):
        prediction, masses, chis, criteria, states = fit_multi(design, target, initial[row], return_states=True)
        mapmass.append(prediction)
        best = np.argmin(criteria)
        bands, parameters = states[best]
        samples, accept = sample_posterior(design, target, parameters, bands, random)
        allsamples.append(samples)
        accepts.append(accept)
        means.append(samples.mean(axis=0))
        medians.append(np.diff(np.median(np.cumsum(samples, axis=1), axis=0), prepend=0))
        if row % 16 == 0:
            print(row, round(time.monotonic() - started, 2), accept, flush=True)
    for name, masses in [('mean', means), ('median', medians), ('map', mapmass)]:
        errors = loss(np.array(masses), cache['truth'], np.linspace(-8, 8, 257))
        print(name, 100 * np.exp(-np.array([errors[:128].mean(), errors[128:].mean()])), flush=True)
    np.savez_compressed('multi_posterior.npz', mean=np.array(means), median=np.array(medians), map=np.array(mapmass), samples=np.array(allsamples), acceptance=np.array(accepts))

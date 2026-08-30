import argparse
import json
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from infer import ASSETS, Likelihood, OUTPUT, load_data
from native import NativeLikelihood


LOWER = np.concatenate((np.full(172, 0.3), np.full(96, -0.12)))
WIDTH = np.concatenate((np.full(172, 0.65), np.full(96, 0.24)))


class Posterior:
    def __init__(self, likelihood, reference):
        self.likelihood = likelihood
        self.reference = reference
        self.total_count = likelihood.count * len(likelihood.betas)

    def evaluate(self, coordinates):
        proportions = expit(coordinates)
        values = LOWER + WIDTH * proportions
        loss, gradient = self.likelihood.evaluate(values)
        potential = self.total_count * (loss - self.reference) + np.sum(np.logaddexp(0, coordinates) + np.logaddexp(0, -coordinates))
        gradient = self.total_count * gradient * WIDTH * proportions * (1 - proportions) + 2 * proportions - 1
        return potential, gradient


def prepare(likelihood):
    fit = np.load(OUTPUT / 'fit.npz')
    posterior = Posterior(likelihood, float(fit['loss']))
    initial = logit(np.clip((fit['theta'] - LOWER) / WIDTH, 0.01, 0.99))
    started = time.monotonic()
    calls = 0

    def objective(coordinates):
        nonlocal calls
        result = posterior.evaluate(coordinates)
        calls += 1
        if calls % 50 == 0:
            print('mode', calls, result[0], np.linalg.norm(result[1]), time.monotonic() - started, flush=True)
        return result

    result = minimize(objective, initial, jac=True, method='L-BFGS-B', options={'maxiter': 1500, 'maxcor': 30, 'ftol': 1e-12, 'gtol': 1e-5})
    print('mode result', result.message, result.fun, np.linalg.norm(result.jac), flush=True)
    center = result.x
    hessian = np.empty((268, 268))
    step = 2e-4
    for parameter in range(268):
        direction = np.zeros(268)
        direction[parameter] = step
        hessian[:, parameter] = (posterior.evaluate(center + direction)[1] - posterior.evaluate(center - direction)[1]) / (2 * step)
    asymmetry = np.max(np.abs(hessian - hessian.T))
    hessian = (hessian + hessian.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(hessian)
    print('hessian eigenvalues', eigenvalues[:10], eigenvalues[-10:], 'asymmetry', asymmetry, flush=True)
    transform = eigenvectors / np.sqrt(np.maximum(eigenvalues, 0.03))[None, :]
    np.savez(OUTPUT / 'posterior_geometry.npz', center=center, transform=transform, hessian=hessian, reference=fit['loss'], theta_mode=LOWER + WIDTH * expit(center))


def run_chain(likelihood, chain, warmup, samples, initial_step, min_steps, max_steps):
    geometry = np.load(OUTPUT / 'posterior_geometry.npz')
    center = geometry['center']
    transform = geometry['transform']
    posterior = Posterior(likelihood, float(geometry['reference']))
    rng = np.random.default_rng(79193 + 173 * chain)

    def objective(whitened):
        potential, gradient = posterior.evaluate(center + transform @ whitened)
        return potential, transform.T @ gradient

    current = rng.normal(size=268) * 0.3
    current_potential, current_gradient = objective(current)
    step = initial_step
    step_average = np.log(initial_step)
    dual_average = 0.0
    target_acceptance = 0.82
    anchor = np.log(initial_step * 10)
    values = np.empty((samples, 268))
    coordinates = np.empty((samples, 268))
    potentials = np.empty(samples)
    probabilities = np.empty(samples)
    accepted = 0
    total_accepted = 0
    started = time.monotonic()
    queries = json.loads((ASSETS / 'input/queries.json').read_text())
    predictive = []
    for iteration in range(warmup + samples):
        momentum = rng.normal(size=268)
        proposal = current.copy()
        proposal_momentum = momentum.copy()
        proposal_potential = current_potential
        proposal_gradient = current_gradient.copy()
        leapfrog_steps = int(rng.integers(min_steps, max_steps + 1))
        integrator_step = step * rng.uniform(0.85, 1.15)
        proposal_momentum -= 0.5 * integrator_step * proposal_gradient
        for leapfrog in range(leapfrog_steps):
            proposal += integrator_step * proposal_momentum
            proposal_potential, proposal_gradient = objective(proposal)
            if leapfrog < leapfrog_steps - 1:
                proposal_momentum -= integrator_step * proposal_gradient
        proposal_momentum -= 0.5 * integrator_step * proposal_gradient
        energy_difference = current_potential + 0.5 * np.dot(momentum, momentum) - proposal_potential - 0.5 * np.dot(proposal_momentum, proposal_momentum)
        acceptance_probability = np.exp(min(0.0, energy_difference)) if np.isfinite(energy_difference) else 0.0
        if rng.random() < acceptance_probability:
            current = proposal
            current_potential = proposal_potential
            current_gradient = proposal_gradient
            accepted += 1
            total_accepted += 1
        if iteration < warmup:
            adaptation_index = iteration + 1
            averaging_weight = 1 / (adaptation_index + 10)
            dual_average = (1 - averaging_weight) * dual_average + averaging_weight * (target_acceptance - acceptance_probability)
            log_step = anchor - np.sqrt(adaptation_index) * dual_average / 0.05
            log_step = np.clip(log_step, np.log(0.001), np.log(1.0))
            step = np.exp(log_step)
            mixing_weight = adaptation_index ** -0.75
            step_average = mixing_weight * log_step + (1 - mixing_weight) * step_average
            if iteration == warmup - 1:
                step = float(np.exp(step_average))
        else:
            index = iteration - warmup
            coordinates[index] = center + transform @ current
            values[index] = LOWER + WIDTH * expit(coordinates[index])
            potentials[index] = current_potential
            probabilities[index] = acceptance_probability
            if index % 10 == 0:
                predictive.append(likelihood.predict(values[index], queries))
        if (iteration + 1) % 100 == 0:
            print('chain', chain, 'iteration', iteration + 1, 'potential', current_potential, 'step', step, 'acceptance', accepted / 100, 'seconds', time.monotonic() - started, flush=True)
            accepted = 0
        if iteration >= warmup and ((iteration - warmup + 1) % 250 == 0 or iteration == warmup + samples - 1):
            completed = iteration - warmup + 1
            np.savez(OUTPUT / f'chain_{chain}.npz', theta=values[:completed], coordinates=coordinates[:completed], potential=potentials[:completed], acceptance=probabilities[:completed], predictive=np.asarray(predictive), step=step)
    print('chain complete', chain, 'acceptance', total_accepted / (warmup + samples), 'seconds', time.monotonic() - started, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--chain', type=int, default=0)
    parser.add_argument('--warmup', type=int, default=600)
    parser.add_argument('--samples', type=int, default=1800)
    parser.add_argument('--step', type=float, default=0.1)
    parser.add_argument('--min-steps', type=int, default=8)
    parser.add_argument('--max-steps', type=int, default=16)
    args = parser.parse_args()
    configurations, betas, spec = load_data()
    likelihood = NativeLikelihood(Likelihood(configurations, betas, spec))
    if args.prepare:
        prepare(likelihood)
    else:
        run_chain(likelihood, args.chain, args.warmup, args.samples, args.step, args.min_steps, args.max_steps)


if __name__ == '__main__':
    main()

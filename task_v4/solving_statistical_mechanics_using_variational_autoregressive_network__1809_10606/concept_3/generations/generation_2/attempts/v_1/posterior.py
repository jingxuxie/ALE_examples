import argparse
import json
import time

from infer import Inference, SOURCE
import numpy as np
from scipy.linalg import cho_factor, cho_solve, cholesky


def reflective_drift(position, momentum, duration, covariance, lower, upper):
    position = position.copy()
    momentum = momentum.copy()
    velocity = covariance @ momentum
    remaining = duration
    collisions = 0
    while remaining > 0:
        with np.errstate(divide="ignore", invalid="ignore"):
            times = np.where(velocity > 0, (upper - position) / velocity, (lower - position) / velocity)
        coordinate = np.argmin(times)
        first_hit = max(times[coordinate], 0.0)
        if first_hit >= remaining:
            position += remaining * velocity
            break
        position += first_hit * velocity
        position[coordinate] = upper[coordinate] if velocity[coordinate] > 0 else lower[coordinate]
        remaining -= first_hit
        change = 2 * velocity[coordinate] / covariance[coordinate, coordinate]
        momentum[coordinate] -= change
        velocity -= change * covariance[:, coordinate]
        collisions += 1
        if collisions > 10000:
            raise RuntimeError("Excessive reflections")
    return np.clip(position, lower, upper), momentum, collisions


def run_chain(inference, theta, covariance, args):
    rng = np.random.default_rng(args.seed)
    covariance = np.ascontiguousarray(covariance)
    precision = cho_solve(cho_factor(covariance, lower=True), np.eye(inference.dimension))
    momentum_factor = cholesky(precision, lower=True)
    value, gradient = inference.scipy_loss(theta)
    step_size = args.step_size
    log_step_average = np.log(step_size)
    dual_center = np.log(10 * step_size)
    error_average = 0.0
    samples = []
    losses = []
    accepted = []
    acceptance_rates = []
    energies = []
    reflections = []
    swap_attempts = 0
    swap_acceptances = 0
    swap_pairs = []
    for hidden_site in inference.hidden:
        incident = np.flatnonzero(np.any(inference.edges == hidden_site, axis=1))
        if len(incident) == 2:
            swap_pairs.append((incident, inference.edge_count + hidden_site))
    started = time.time()
    total_steps = args.warmup + args.samples
    for iteration in range(total_steps):
        momentum = momentum_factor @ rng.normal(size=inference.dimension)
        initial_energy = value + 0.5 * momentum @ covariance @ momentum
        proposal = theta.copy()
        proposal_gradient = gradient.copy()
        proposal_momentum = momentum - 0.5 * step_size * proposal_gradient
        leapfrogs = rng.integers(args.min_steps, args.max_steps + 1)
        total_reflections = 0
        for leapfrog in range(leapfrogs):
            proposal, proposal_momentum, collisions = reflective_drift(
                proposal, proposal_momentum, step_size, covariance, inference.lower, inference.upper)
            total_reflections += collisions
            proposal_value, proposal_gradient = inference.scipy_loss(proposal)
            proposal_momentum -= (0.5 if leapfrog == leapfrogs - 1 else 1.0) * step_size * proposal_gradient
        final_energy = proposal_value + 0.5 * proposal_momentum @ covariance @ proposal_momentum
        energy_difference = initial_energy - final_energy
        accept_probability = np.exp(min(0, energy_difference)) if np.isfinite(energy_difference) else 0.0
        accept = rng.uniform() < accept_probability
        if accept:
            theta, value, gradient = proposal, proposal_value, proposal_gradient
        if args.swaps and rng.uniform() < 0.25:
            pair, field_index = swap_pairs[rng.integers(len(swap_pairs))]
            alternative = theta.copy()
            alternative[pair] = alternative[pair[::-1]]
            if rng.uniform() < 0.5:
                alternative[field_index] *= -1
            alternative_value, alternative_gradient = inference.scipy_loss(alternative)
            swap_attempts += 1
            if np.log(rng.uniform()) < value - alternative_value:
                theta, value, gradient = alternative, alternative_value, alternative_gradient
                swap_acceptances += 1
        if iteration < args.warmup:
            iteration_count = iteration + 1
            eta = 1 / (iteration_count + 10)
            error_average = (1 - eta) * error_average + eta * (args.target_accept - accept_probability)
            log_step = dual_center - np.sqrt(iteration_count) / 0.05 * error_average
            average_weight = iteration_count ** -0.75
            log_step_average = average_weight * log_step + (1 - average_weight) * log_step_average
            step_size = np.clip(np.exp(log_step), 0.005, 0.6)
            if iteration_count == args.warmup:
                step_size = float(np.exp(log_step_average))
                print("warmup complete", "step_size", step_size, "elapsed", time.time() - started, flush=True)
        else:
            samples.append(theta.copy())
            losses.append(value)
            accepted.append(accept)
            acceptance_rates.append(accept_probability)
            energies.append(energy_difference)
            reflections.append(total_reflections)
        if (iteration + 1) % 100 == 0:
            recent_acceptance = np.mean(accepted[-100:]) if accepted else accept_probability
            print("iteration", iteration + 1, "nll", value, "acceptance", recent_acceptance,
                  "step", step_size, "reflections", total_reflections,
                  "swaps", (swap_acceptances, swap_attempts),
                  "elapsed", time.time() - started, flush=True)
        if samples and ((iteration + 1) % 250 == 0 or iteration + 1 == total_steps):
            np.savez(args.output, samples=np.asarray(samples), losses=losses, accepted=accepted,
                     acceptance_rates=acceptance_rates, energy_differences=energies,
                     reflections=reflections, covariance=covariance, step_size=step_size, seed=args.seed)
    return np.asarray(samples)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit", default="fit.npz")
    parser.add_argument("--samples", type=int, default=3000)
    parser.add_argument("--warmup", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="chain.npz")
    parser.add_argument("--step-size", type=float, default=0.15)
    parser.add_argument("--min-steps", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=24)
    parser.add_argument("--target-accept", type=float, default=0.8)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--resume", type=str)
    parser.add_argument("--swaps", action="store_true")
    args = parser.parse_args()
    inference = Inference()
    theta = np.load(args.fit)["theta"]
    if args.prepare:
        hessian = inference.hessian(theta)
        eigenvalues = np.linalg.eigvalsh(hessian)
        print("Hessian eigenvalues", eigenvalues[:15], eigenvalues[-5:], flush=True)
        np.save("fit_hessian.npy", hessian)
        regularized = hessian + np.diag(12 / (inference.upper - inference.lower) ** 2)
        eigenvalues, eigenvectors = np.linalg.eigh(regularized)
        print("Regularized eigenvalues", eigenvalues[:10], flush=True)
        covariance = (eigenvectors / np.maximum(eigenvalues, 10)) @ eigenvectors.T
        np.save("mass_covariance.npy", covariance)
        tiny = Inference(inference.observations[:, :3, :])
        calculated = tiny.scipy_loss(theta)[0]
        from transfer import model_from_edges
        model = model_from_edges(inference.spec, theta[:172] * inference.signs, theta[172:])
        expected = 0.0
        for condition, beta in enumerate(inference.betas):
            partition = model.log_partition(beta)
            for observation in tiny.observations[condition]:
                evidence = np.zeros(96, dtype=np.int8)
                evidence[inference.visible] = observation
                expected += partition - model.log_partition(beta, evidence=evidence.reshape(12, 8))
        np.testing.assert_allclose(calculated, expected, rtol=1e-11, atol=1e-9)
        print("Exact clamped likelihood test passed", calculated, expected, flush=True)
        rng = np.random.default_rng(77)
        position = (inference.lower + inference.upper) / 2
        momentum = rng.normal(size=268) * 100
        next_position, next_momentum, collisions = reflective_drift(position, momentum, 0.3, covariance, inference.lower, inference.upper)
        return_position, return_momentum, _ = reflective_drift(next_position, -next_momentum, 0.3, covariance, inference.lower, inference.upper)
        np.testing.assert_allclose(position, return_position, atol=1e-10)
        np.testing.assert_allclose(momentum, -return_momentum, atol=1e-9)
        np.testing.assert_allclose(momentum @ covariance @ momentum, next_momentum @ covariance @ next_momentum, rtol=1e-12)
        print("Reflection reversibility and energy tests passed", collisions, flush=True)
        return
    covariance = np.load("mass_covariance.npy")
    if args.resume:
        previous = np.load(args.resume)
        theta = previous["samples"][-1].copy()
        covariance = previous["covariance"]
        args.step_size = float(previous["step_size"])
    run_chain(inference, theta, covariance, args)


if __name__ == "__main__":
    main()

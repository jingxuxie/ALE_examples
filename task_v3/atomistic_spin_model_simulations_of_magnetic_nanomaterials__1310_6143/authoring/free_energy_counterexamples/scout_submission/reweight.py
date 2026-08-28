import math

import numpy as np


def symmetric_potentials(coefficients, angles, temperature):
    harmonics = np.array([2.0, 4.0])
    arguments = np.asarray(angles)[:, None] * harmonics
    even = coefficients[:, [2, 4]] @ np.cos(arguments).T
    odd = coefficients[:, [3, 5]] @ np.sin(arguments).T
    scaled = odd / temperature
    absolute = np.abs(scaled)
    potential = even / temperature - absolute - np.log1p(np.exp(-2 * absolute)) + math.log(2)
    torque = coefficients[:, [2, 4]] @ (harmonics * np.sin(arguments)).T
    torque += np.tanh(scaled) * (coefficients[:, [3, 5]] @ (harmonics * np.cos(arguments)).T)
    return potential, torque


def fit_mbar(potential, labels, initial=None):
    state_count = potential.shape[1]
    counts = np.bincount(labels, minlength=state_count).astype(float)
    if np.any(counts == 0):
        raise ValueError("Missing reweighting state")
    offset = potential.mean(axis=0)
    centered = potential - offset
    free = np.zeros(state_count) if initial is None else initial - offset + offset[0]
    shift = -centered.min(axis=1)
    density = np.exp(-centered - shift[:, None])
    if initial is None:
        for warmup in range(30):
            maximum = free.max()
            denominator = density @ (counts * np.exp(free - maximum))
            candidate = -np.log(density.T @ (1 / denominator))
            candidate -= candidate[0]
            change = np.max(np.abs(candidate - free))
            free = candidate
            if change < 1e-7:
                break
    for iteration in range(60):
        maximum = free.max()
        activity = counts * np.exp(free - maximum)
        denominator = density @ activity
        probability = density * (activity[None, :] / denominator[:, None])
        totals = probability.sum(axis=0)
        gradient = totals - counts
        if np.max(np.abs(gradient) / counts) < 2e-10:
            break
        hessian = np.diag(totals) - probability.T @ probability
        direction = np.zeros(state_count)
        direction[1:] = np.linalg.solve(hessian[1:, 1:], gradient[1:])
        objective = np.log(denominator).sum() + len(labels) * maximum - counts @ free
        slope = gradient @ direction
        scale = 1.0
        for search in range(30):
            candidate = free - scale * direction
            candidate_maximum = candidate.max()
            candidate_denominator = density @ (counts * np.exp(candidate - candidate_maximum))
            candidate_objective = np.log(candidate_denominator).sum() + len(labels) * candidate_maximum - counts @ candidate
            if candidate_objective <= objective - 1e-4 * scale * slope + 1e-8:
                free = candidate
                break
            scale *= 0.5
        else:
            raise ArithmeticError("Multistate reweighting did not converge")
    else:
        raise ArithmeticError("Multistate reweighting exceeded iteration limit")
    maximum = free.max()
    denominator = density @ (counts * np.exp(free - maximum))
    log_denominator = np.log(denominator) + shift + maximum - offset[0]
    return free + offset - offset[0], log_denominator


def evaluate(potential, torque, log_denominator, temperature, spin_count):
    log_weight = -potential - log_denominator[:, None]
    maximum = log_weight.max(axis=0)
    weights = np.exp(log_weight - maximum)
    normalization = weights.sum(axis=0)
    log_partition = np.log(normalization) + maximum
    free = -temperature * (log_partition - log_partition[0]) / spin_count
    average_torque = (weights * torque).sum(axis=0) / normalization / spin_count
    effective = normalization**2 / (weights**2).sum(axis=0)
    return average_torque, free, effective


def reweight(samples, angles, requested, temperature, spin_count):
    labels = samples[:, 0].astype(int)
    folds = samples[:, 1].astype(int) // 8
    coefficients = samples[:, 2:]
    training_potential, _ = symmetric_potentials(coefficients, angles, temperature)
    target_angles = np.concatenate(([0.0], np.asarray(requested)))
    target_potential, target_torque = symmetric_potentials(coefficients, target_angles, temperature)
    fitted, denominator = fit_mbar(training_potential, labels)
    torque, free, effective = evaluate(target_potential, target_torque, denominator, temperature, spin_count)
    jackknife_torque, jackknife_free = [], []
    for fold in range(8):
        retained = folds != fold
        _, partial_denominator = fit_mbar(training_potential[retained], labels[retained], fitted)
        partial_torque, partial_free, _ = evaluate(target_potential[retained], target_torque[retained],
                                                  partial_denominator, temperature, spin_count)
        jackknife_torque.append(partial_torque)
        jackknife_free.append(partial_free)
    torque_sem = np.std(jackknife_torque, axis=0, ddof=0) * math.sqrt(7)
    free_sem = np.std(jackknife_free, axis=0, ddof=0) * math.sqrt(7)
    torque = torque[1:]
    free = free[1:]
    torque[np.abs(np.sin(2 * np.asarray(requested))) < 1e-14] = 0.0
    free[0] = 0.0
    return {"torque": torque.tolist(), "free_energy": free.tolist(),
            "torque_sem": torque_sem[1:].tolist(), "free_energy_sem": free_sem[1:].tolist(),
            "reweighting_effective_samples": effective[1:].tolist(),
            "reweighting_samples": len(samples), "method": "directional-exchange-MC/symmetric-MBAR"}

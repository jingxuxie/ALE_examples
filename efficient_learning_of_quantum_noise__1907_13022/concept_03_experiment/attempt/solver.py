import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import warnings
import numpy as np
from scipy.special import rel_entr


def hadamard(values):
    result = np.array(values, dtype=np.float64, copy=True)
    size = result.shape[-1]
    stride = 1
    while stride < size:
        view = result.reshape(-1, size // (2 * stride), 2, stride)
        left = view[:, :, 0, :].copy()
        right = view[:, :, 1, :].copy()
        view[:, :, 0, :] = left + right
        view[:, :, 1, :] = left - right
        stride *= 2
    return result


def simplex(values):
    ordered = np.sort(values)[::-1]
    offsets = (np.cumsum(ordered) - 1.0) / np.arange(1, len(values) + 1)
    active = np.flatnonzero(ordered > offsets)
    threshold = offsets[active[-1]] if len(active) else offsets[-1]
    result = np.maximum(values - threshold, 0.0)
    return result / result.sum()


def exponential_fit(times, observed, weights, rates, iterations=18):
    span = max(float(np.ptp(times)), 1.0)
    rate_limit = 30.0 / max(float(np.min(np.diff(np.unique(times)))), 1.0)
    rates = np.clip(rates.copy(), 0.0, rate_limit)
    for iteration in range(iterations):
        basis = np.exp(-times[:, None] * rates[None, :])
        norm = np.maximum(np.sum(weights * basis * basis, axis=0), 1e-280)
        amplitudes = np.sum(weights * basis * observed, axis=0) / norm
        amplitudes = np.maximum(amplitudes, 1e-12)
        residual = observed - basis * amplitudes[None, :]
        mean_time = np.sum(weights * basis * basis * times[:, None], axis=0) / norm
        centered = times[:, None] - mean_time[None, :]
        curvature = np.sum(weights * basis * basis * centered * centered, axis=0)
        numerator = np.sum(weights * basis * centered * residual, axis=0)
        step = -numerator / np.maximum(amplitudes * curvature, 1e-280)
        limit = np.maximum(0.7 * rates, 0.7 / span)
        step = np.clip(step, -limit, limit)
        previous_loss = np.sum(weights * residual * residual, axis=0)
        proposed = np.clip(rates + step, 0.0, rate_limit)
        for backtrack in range(8):
            trial_basis = np.exp(-times[:, None] * proposed[None, :])
            trial_norm = np.maximum(np.sum(weights * trial_basis * trial_basis, axis=0), 1e-280)
            trial_amplitude = np.maximum(np.sum(weights * trial_basis * observed, axis=0) / trial_norm, 1e-12)
            trial_loss = np.sum(weights * (observed - trial_basis * trial_amplitude[None, :]) ** 2, axis=0)
            rejected = trial_loss > previous_loss * (1.0 + 1e-12) + 1e-25
            if not np.any(rejected):
                break
            proposed[rejected] = 0.5 * (proposed[rejected] + rates[rejected])
        difference = np.max(np.abs(proposed - rates) / (rates + 1.0 / span))
        rates = proposed
        if difference < 1e-7:
            break
    basis = np.exp(-times[:, None] * rates[None, :])
    norm = np.maximum(np.sum(weights * basis * basis, axis=0), 1e-280)
    amplitudes = np.maximum(np.sum(weights * basis * observed, axis=0) / norm, 1e-12)
    return rates, amplitudes, basis


def fit_modes(counts, depths):
    shots = np.sum(counts, axis=1)
    valid = shots > 0
    counts = np.asarray(counts[valid], dtype=np.float64)
    depths = np.asarray(depths[valid], dtype=np.float64)
    shots = shots[valid].astype(np.float64)
    order = np.argsort(depths, kind="stable")
    depths, shots, counts = depths[order], shots[order], counts[order]
    size = counts.shape[1]
    frequencies = counts / shots[:, None]
    spectrum = hadamard(frequencies)
    if size == 1:
        return np.ones(1), np.zeros(1), {}
    if len(np.unique(depths)) < 2:
        return np.ones(size), np.full(size, np.inf), {}
    times = depths - depths[0]
    observed = spectrum[:, 1:].copy()
    shot_variance = np.maximum(1.0 - observed * observed, 1.0 / shots[:, None]) / shots[:, None]
    strength = np.abs(observed) / np.sqrt(shot_variance)
    depth_parity = np.remainder(np.rint(depths).astype(np.int64), 2)
    alternating = np.zeros(size - 1, dtype=bool)
    if np.any(depth_parity == 0) and np.any(depth_parity == 1):
        even_index = np.argmax(np.where(depth_parity[:, None] == 0, strength, -1.0), axis=0)
        odd_index = np.argmax(np.where(depth_parity[:, None] == 1, strength, -1.0), axis=0)
        columns = np.arange(size - 1)
        even_value, odd_value = observed[even_index, columns], observed[odd_index, columns]
        early_limit = np.unique(depths)[1]
        early_contrast = (depths[even_index] <= early_limit) & (depths[odd_index] <= early_limit)
        alternating = ((even_value * odd_value < 0.0) & (strength[even_index, columns] > 6.0)
                       & (strength[odd_index, columns] > 6.0)
                       & (early_contrast | (np.minimum(np.abs(even_value), np.abs(odd_value))
                                            > 0.04 * np.maximum(np.abs(even_value), np.abs(odd_value)))))
    phase = np.where((depth_parity[:, None] != depth_parity[0]) & alternating[None, :], -1.0, 1.0)
    observed *= phase
    strongest = np.argmax(strength, axis=0)
    signs = np.sign(observed[strongest, np.arange(size - 1)])
    signs[signs == 0.0] = 1.0
    observed *= signs[None, :]
    peak = np.maximum(np.max(observed, axis=0), 1e-8)
    usable = (observed > 0.12 * peak[None, :]) & (observed > 3.0 * np.sqrt(shot_variance))
    log_weights = np.where(usable, observed * observed / shot_variance, 0.0)
    log_weights /= np.maximum(np.max(log_weights, axis=0), 1e-100)
    log_values = np.log(np.maximum(observed, 1e-12))
    total = np.maximum(np.sum(log_weights, axis=0), 1e-100)
    mean_time = np.sum(log_weights * times[:, None], axis=0) / total
    mean_log = np.sum(log_weights * log_values, axis=0) / total
    centered = times[:, None] - mean_time[None, :]
    denominator = np.sum(log_weights * centered * centered, axis=0)
    rates = -np.sum(log_weights * centered * (log_values - mean_log[None, :]), axis=0) / np.maximum(denominator, 1e-100)
    rates = np.maximum(rates, 0.0)
    span = max(float(np.ptp(times)), 1.0)
    rates[denominator < 1e-12] = 1.0 / span
    window = times[:, None] * rates[None, :] <= 3.5
    window[: min(4, len(times)), :] = True
    weights = window / shot_variance
    weights /= np.maximum(np.max(weights, axis=0), 1e-100)
    rates, amplitudes, basis = exponential_fit(times, observed, weights, rates)
    excess_variance = np.zeros(size - 1)
    for robust_iteration in range(3):
        prediction = basis * amplitudes[None, :]
        residual = observed - prediction
        window = times[:, None] * rates[None, :] <= 3.5
        window[: min(4, len(times)), :] = True
        useful = window & (prediction > 2.0 * np.sqrt(shot_variance))
        selected = np.where(useful, residual * residual, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            residual_variance = np.nanmedian(selected, axis=0) / 0.4549364231
            typical_shot = np.nanmedian(np.where(useful, shot_variance, np.nan), axis=0)
        sample_count = np.sum(useful, axis=0)
        correction = sample_count / np.maximum(sample_count - 2.0, 1.0)
        new_excess = np.maximum(residual_variance * correction - typical_shot, 0.0)
        new_excess = np.nan_to_num(new_excess, nan=0.0, posinf=0.0, neginf=0.0)
        excess_variance = new_excess if robust_iteration == 0 else 0.5 * (excess_variance + new_excess)
        variance = shot_variance + excess_variance[None, :]
        standardized = residual / np.sqrt(variance)
        weights = window / variance / np.sqrt(1.0 + (standardized / 2.5) ** 2)
        weights /= np.maximum(np.max(weights, axis=0), 1e-100)
        rates, amplitudes, basis = exponential_fit(times, observed, weights, rates, iterations=12)
    norm = np.maximum(np.sum(weights * basis * basis, axis=0), 1e-280)
    mean_time = np.sum(weights * basis * basis * times[:, None], axis=0) / norm
    centered = times[:, None] - mean_time[None, :]
    curvature = np.sum(weights * basis * basis * centered * centered, axis=0)
    eigenvalues = np.where(alternating, -1.0, 1.0) * np.exp(-rates)
    influence = eigenvalues[None, :] * weights * basis * centered / np.maximum(amplitudes * curvature, 1e-280)[None, :]
    eigen_variance = np.sum(influence * influence * variance, axis=0)
    amplitude_influence = weights * basis / norm[None, :] - mean_time[None, :] * weights * basis * centered / np.maximum(curvature, 1e-280)[None, :]
    amplitude_variance = np.sum(amplitude_influence * amplitude_influence * variance, axis=0)
    reliable = ((amplitudes > 3.0 * np.sqrt(amplitude_variance)) & (curvature > 1e-270)
                & np.isfinite(eigen_variance) & (eigen_variance < 0.25))
    eigen_variance[~reliable] = np.inf
    eigen_variance = np.maximum(eigen_variance, 1e-16)
    result = np.r_[1.0, eigenvalues]
    uncertainty = np.r_[0.0, eigen_variance]
    details = {"spectrum": spectrum, "frequencies": frequencies, "shots": shots,
               "times": times, "amplitudes": amplitudes, "rates": rates,
               "influence": influence * signs[None, :] * phase, "variance": variance,
               "excess_variance": excess_variance}
    return result, uncertainty, details


def reconstruct(counts, depths):
    eigenvalues, uncertainty, details = fit_modes(counts, depths)
    size = len(eigenvalues)
    qubits = size.bit_length() - 1
    states = np.arange(size)
    prior_modes = np.ones(size)
    for qubit in range(qubits):
        singleton = 1 << qubit
        value = eigenvalues[singleton] if np.isfinite(uncertainty[singleton]) else 1.0
        prior_modes *= np.where(states & singleton, value, 1.0)
    missing = ~np.isfinite(uncertainty)
    eigenvalues[missing] = prior_modes[missing]
    raw = hadamard(eigenvalues) / size
    if np.min(raw) >= -1e-12:
        result = np.maximum(raw, 0.0)
        return result / result.sum()
    good = np.isfinite(uncertainty[1:])
    if not np.any(good):
        return simplex(hadamard(prior_modes) / size)
    reference_variance = np.median(uncertainty[1:][good])
    weights = reference_variance / np.maximum(uncertainty, 1e-16)
    weights[0] = 0.0
    probabilities = simplex(raw)
    dual = np.zeros(size)
    penalty = 1.0
    best_probabilities = probabilities.copy()
    best_loss = np.sum(weights * (hadamard(probabilities) - eigenvalues) ** 2)
    for iteration in range(2500):
        spectrum = hadamard(probabilities - dual)
        spectrum = (weights * eigenvalues + penalty * spectrum) / (weights + penalty)
        unconstrained = hadamard(spectrum) / size
        relaxed = 1.6 * unconstrained - 0.6 * probabilities
        updated = simplex(relaxed + dual)
        dual += relaxed - updated
        primal_residual = unconstrained - updated
        dual_residual = penalty * (updated - probabilities)
        change = np.max(np.abs(updated - probabilities))
        probabilities = updated
        if iteration > 40 and np.max(np.abs(primal_residual)) < 2e-10 and change < 2e-10:
            break
        if iteration % 25 == 24:
            loss = np.sum(weights * (hadamard(probabilities) - eigenvalues) ** 2)
            if loss < best_loss:
                best_loss = loss
                best_probabilities = probabilities.copy()
            primal_norm = np.linalg.norm(primal_residual)
            dual_norm = np.linalg.norm(dual_residual)
            if primal_norm > 10.0 * dual_norm and penalty < 1e4:
                penalty *= 2.0
                dual *= 0.5
            elif dual_norm > 10.0 * primal_norm and penalty > 1e-4:
                penalty *= 0.5
                dual *= 2.0
    loss = np.sum(weights * (hadamard(probabilities) - eigenvalues) ** 2)
    if best_loss < loss:
        probabilities = best_probabilities
    return probabilities / probabilities.sum()


def mask_integer(mask):
    result = 0
    for qubit in np.flatnonzero(mask):
        result |= 1 << int(qubit)
    return result


def diagnostics(probabilities, blocks, conditional_queries, parents):
    size = len(probabilities)
    states = np.arange(size, dtype=np.int64)
    event_masks = [mask_integer(block) for block in blocks]
    events = np.array([(states & mask) != 0 for mask in event_masks], dtype=np.float64).reshape(len(blocks), size)
    means = events @ probabilities
    variance = np.maximum(means * (1.0 - means), 0.0)
    covariance = (events * probabilities[None, :]) @ events.T - np.outer(means, means)
    denominator = np.sqrt(np.outer(variance, variance))
    correlations = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0)
    correlations = np.clip(correlations, -1.0, 1.0)
    np.fill_diagonal(correlations, (variance > 0).astype(float))
    entropy_cache = {0: 0.0}

    def entropy(mask):
        if mask not in entropy_cache:
            marginal = np.bincount(states & mask, weights=probabilities, minlength=mask + 1)
            positive = marginal[marginal > 0.0]
            entropy_cache[mask] = -np.sum(positive * np.log(positive))
        return entropy_cache[mask]

    information = []
    for query in conditional_queries:
        mask_x, mask_y, mask_z = [mask_integer(part) for part in query]
        value = entropy(mask_x | mask_z) + entropy(mask_y | mask_z) - entropy(mask_z) - entropy(mask_x | mask_y | mask_z)
        information.append(max(0.0, float(value)))
    spatial = np.ones(size)
    for child, parent_row in enumerate(parents):
        parent_mask = mask_integer(parent_row)
        child_mask = 1 << child
        parent_index = states & parent_mask
        parent_probability = np.bincount(parent_index, weights=probabilities, minlength=parent_mask + 1)
        joint_index = states & (parent_mask | child_mask)
        joint_probability = np.bincount(joint_index, weights=probabilities, minlength=(parent_mask | child_mask) + 1)
        conditional = np.divide(joint_probability[joint_index], parent_probability[parent_index],
                                out=np.full(size, 0.5), where=parent_probability[parent_index] > 0.0)
        spatial *= conditional
    spatial /= spatial.sum()
    midpoint = 0.5 * (probabilities + spatial)
    divergence = 0.5 * np.sum(rel_entr(probabilities, midpoint) + rel_entr(spatial, midpoint)) / np.log(2.0)
    return correlations, np.asarray(information), np.asarray(np.sqrt(max(0.0, divergence)))


def solve(input_path, output_path):
    with np.load(input_path, allow_pickle=False) as data:
        counts = np.asarray(data["counts"], dtype=np.float64)
        probabilities = reconstruct(counts, data["depths"])
        correlations, information, distance = diagnostics(probabilities, data["blocks"], data["conditional_queries"], data["parents"])
    np.savez(output_path, probabilities=probabilities, correlations=correlations,
             conditional_information=information, spatial_jsd=distance)


if __name__ == "__main__":
    solve(*sys.argv[1:])

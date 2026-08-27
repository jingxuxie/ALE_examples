import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, softmax


def prepare_calibration(metadata, records):
    probes = {probe['id']: probe for probe in metadata['probes']}
    prepared = []
    group_count = metadata['rate_groups']
    for setting in metadata['settings']:
        probe = probes[setting['probe']]
        faults = probe['faults']
        states = np.arange(1 << len(faults), dtype=np.uint32)
        labels = np.zeros(len(states), dtype=np.int64)
        counts = np.zeros((len(states), group_count))
        gains = np.zeros(len(states))
        group_indices = []
        biases = []
        for index, fault in enumerate(faults):
            bits = ((states >> index) & 1).astype(float)
            counts[:, fault['rate_group']] += bits
            gains += bits * fault['bias']
            labels ^= bits.astype(np.int64) * sum(1 << detector for detector in fault['detectors'])
            group_indices.append(fault['rate_group'])
            biases.append(fault['bias'])
        prepared.append((counts, gains, labels, np.asarray(group_indices), np.asarray(biases), setting['dose']))
    return prepared, records['setting'].astype(int), records['syndrome'].astype(int), group_count


def unpack(parameters, mode_count, group_count):
    cursor = mode_count * group_count
    offsets = parameters[:cursor].reshape(mode_count, group_count)
    slopes = parameters[cursor:cursor + group_count]
    cursor += group_count
    initial = softmax(np.r_[parameters[cursor:cursor + mode_count - 1], 0.0])
    cursor += mode_count - 1
    transition = softmax(np.column_stack([parameters[cursor:].reshape(mode_count, mode_count - 1),
                                         np.zeros(mode_count)]), axis=1)
    return offsets, slopes, initial, transition


def likelihood(parameters, mode_count, calibration, need_gradient=True):
    prepared, settings, syndromes, group_count = calibration
    offsets, slopes, initial, transition = unpack(parameters, mode_count, group_count)
    parameter_count = len(parameters)
    max_label = max(int(entry[2].max()) for entry in prepared) + 1
    emission = np.zeros((len(prepared), max_label, mode_count))
    derivative = np.zeros(emission.shape + (parameter_count,))
    for setting_index, (counts, gains, labels, groups, biases, dose) in enumerate(prepared):
        for mode in range(mode_count):
            log_odds = offsets[mode] + slopes * dose
            rates = expit(log_odds[groups] + biases)
            weights = np.exp(counts @ log_odds + gains + np.log1p(-rates).sum())
            emission[setting_index, :, mode] = np.bincount(labels, weights=weights, minlength=max_label)
            expected_counts = np.bincount(groups, weights=rates, minlength=group_count)
            for group in range(group_count):
                changes = np.bincount(labels, weights=weights * (counts[:, group] - expected_counts[group]),
                                      minlength=max_label)
                derivative[setting_index, :, mode, mode * group_count + group] = changes
                derivative[setting_index, :, mode, mode_count * group_count + group] = dose * changes
    initial_derivative = np.zeros((mode_count, parameter_count))
    transition_derivative = np.zeros((mode_count, mode_count, parameter_count))
    cursor = mode_count * group_count + group_count
    for column in range(mode_count - 1):
        initial_derivative[:, cursor + column] = initial * ((np.arange(mode_count) == column) - initial[column])
    cursor += mode_count - 1
    for row in range(mode_count):
        for column in range(mode_count - 1):
            transition_derivative[row, :, cursor + row * (mode_count - 1) + column] = (
                transition[row] * ((np.arange(mode_count) == column) - transition[row, column]))
    batch_count, length = settings.shape
    forward = np.broadcast_to(initial, (batch_count, mode_count)).copy()
    forward_derivative = np.broadcast_to(initial_derivative, (batch_count, mode_count, parameter_count)).copy()
    log_likelihood = 0.0
    gradient = np.zeros(parameter_count)
    for step in range(length):
        if step:
            forward_derivative = (np.einsum('bmp,mn->bnp', forward_derivative, transition, optimize=True)
                                  + np.einsum('bm,mnp->bnp', forward, transition_derivative, optimize=True))
            forward = forward @ transition
        probability = emission[settings[:, step], syndromes[:, step]]
        probability_derivative = derivative[settings[:, step], syndromes[:, step]]
        product = forward * probability
        product_derivative = forward_derivative * probability[:, :, None] + forward[:, :, None] * probability_derivative
        normalizer = product.sum(axis=1)
        normalizer_derivative = product_derivative.sum(axis=1)
        if np.any(normalizer <= 0):
            return 1e20, np.zeros(parameter_count)
        log_likelihood += np.log(normalizer).sum()
        gradient += (normalizer_derivative / normalizer[:, None]).sum(axis=0)
        forward = product / normalizer[:, None]
        forward_derivative = (product_derivative - forward[:, :, None] * normalizer_derivative[:, None, :]) / normalizer[:, None, None]
    return -float(log_likelihood) / batch_count, -gradient / batch_count


def fit(metadata, records, modes=(1, 2, 3), starts=2, maxiter=160):
    calibration = prepare_calibration(metadata, records)
    group_count = metadata['rate_groups']
    random = np.random.default_rng(49281)
    fits = []
    for mode_count in modes:
        best = None
        for restart in range(starts if mode_count > 1 else 1):
            probabilities = np.full((mode_count, group_count), 0.055)
            for mode in range(mode_count):
                probabilities[mode, mode % group_count] = 0.20
            offsets = np.log(probabilities / (1 - probabilities)) + random.normal(0, 0.3, probabilities.shape)
            slopes = random.normal(0, 0.15, group_count)
            initial_logits = np.zeros(mode_count - 1)
            transition = np.full((mode_count, mode_count), 0.1 / max(1, mode_count - 1))
            np.fill_diagonal(transition, 0.9)
            transition /= transition.sum(axis=1, keepdims=True)
            transition_logits = np.log(transition[:, :-1] / transition[:, -1:])
            initial = np.r_[offsets.ravel(), slopes, initial_logits, transition_logits.ravel()]
            bounds = [(-6, 1)] * (mode_count * group_count) + [(-2, 2)] * group_count
            bounds += [(-7, 7)] * (len(initial) - len(bounds))
            started = time.monotonic()
            result = minimize(likelihood, initial, args=(mode_count, calibration), jac=True,
                              method='L-BFGS-B', bounds=bounds,
                              options={'maxiter': maxiter, 'ftol': 2e-10, 'gtol': 2e-6, 'maxls': 30})
            record = {'modes': mode_count, 'restart': restart, 'negative_log_likelihood_per_batch': float(result.fun),
                      'iterations': int(result.nit), 'success': bool(result.success),
                      'seconds': round(time.monotonic() - started, 3)}
            print(json.dumps(record), flush=True)
            if best is None or result.fun < best[0].fun:
                best = result, record
        result, record = best
        record['bic'] = 2 * result.fun * len(records['setting']) + len(result.x) * math.log(records['setting'].size)
        fits.append((record['bic'], result, mode_count, record))
    _, result, mode_count, _ = min(fits, key=lambda entry: entry[0])
    offsets, slopes, initial, transition = unpack(result.x, mode_count, group_count)
    ordering = np.argsort(offsets[:, 0])
    return {'offsets': offsets[ordering].tolist(), 'slopes': slopes.tolist(), 'initial': initial[ordering].tolist(),
            'transition': transition[np.ix_(ordering, ordering)].tolist(),
            'fit_summary': [entry[3] for entry in fits]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--records', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--starts', type=int, default=2)
    parser.add_argument('--maxiter', type=int, default=160)
    arguments = parser.parse_args()
    metadata = json.loads(Path(arguments.calibration).read_text())
    records = np.load(arguments.records)
    model = fit(metadata, records, starts=arguments.starts, maxiter=arguments.maxiter)
    Path(arguments.output).write_text(json.dumps(model, indent=2) + '\n')


if __name__ == '__main__':
    main()

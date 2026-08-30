import argparse
import time

import numpy as np

from acquisition import CANDIDATES, DESIGN, UNKNOWN, acquire, prior
from experiment import ORDERS, report, transform
from global_model import local_predict


def ensemble_features(terms, mean, queries, observed_tails):
    selected = np.array([np.flatnonzero(CANDIDATES == mask)[0] for mask in queries])
    design = DESIGN[selected]
    features = []
    for mode, fifth in [(0, .25), (0, 1), (0, 2), (0, 4), (0, 8), (1, 2), (2, 2), (3, 2)]:
        covariance = prior(terms, fifth_weight=fifth, scale_mode=mode)
        kernel = design @ covariance @ design.T
        weights = np.linalg.solve(kernel + np.eye(len(queries)) * 1e-22, design @ covariance @ np.ones(len(UNKNOWN)))
        coefficients = 1 - weights @ design
        features.append(weights @ observed_tails)
        features.append(coefficients @ np.where(ORDERS[UNKNOWN] == 4, mean[UNKNOWN], 0))
        features.append(coefficients @ np.where(ORDERS[UNKNOWN] >= 5, mean[UNKNOWN], 0))
    features = np.array(features)
    base = sum(features[6:9])
    differences = features.copy()
    differences[::3] -= base
    return differences, base


def prepare(path='ensemble_data.npz', source='train.npz', tail=1800):
    data = np.load(source)
    energies, orbitals, families = data['energies'][-tail:], data['orbitals'][-tail:], data['families'][-tail:]
    means = local_predict(energies, orbitals, families)
    terms = transform(energies)
    rows, targets, bases = [], [], []
    started = time.time()
    for index, (row, mean, family) in enumerate(zip(terms, means, families)):
        queries, _, _ = acquire(row, prior(row, fifth_weight=2), mean=mean, power=.8, return_queries=True)
        observed_tails = ((queries[:, None] & UNKNOWN[None, :]) == UNKNOWN[None, :]) @ row[UNKNOWN]
        features, base = ensemble_features(row, mean, queries, observed_tails)
        rows.append(features)
        targets.append(row[UNKNOWN].sum() - base)
        bases.append(base)
        if index % 300 == 299:
            print('prepare', index + 1, time.time() - started, flush=True)
    np.savez_compressed(path, inputs=rows, targets=targets, bases=bases, families=families)


def train():
    data = np.load('ensemble_data.npz')
    families = data['families']
    for ridge in [.01, .1, 1, 10, 100]:
        predictions = np.zeros(len(families))
        weights = []
        scales = []
        for family in range(6):
            selected = families == family
            training = selected & (np.arange(len(families)) < 1200)
            inputs = data['inputs'][training]
            scale = np.maximum(np.sqrt(np.mean(inputs ** 2, axis=0)), 1e-7)
            inputs = inputs / scale
            coefficients = np.linalg.solve(inputs.T @ inputs + ridge * np.eye(inputs.shape[1]), inputs.T @ data['targets'][training])
            predictions[selected] = data['inputs'][selected] / scale @ coefficients
            weights.append(coefficients)
            scales.append(scale)
        errors = predictions - data['targets']
        report(errors[1200:], families[1200:], 'ridge ' + str(ridge))
        np.savez('ensemble' + str(ridge) + '.npz', weights=weights, scales=scales)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    arguments = parser.parse_args()
    if arguments.prepare:
        prepare()
    train()

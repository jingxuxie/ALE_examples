import argparse
import time

import numpy as np

from experiment import MASKS, ORDERS, SUBSETS, report, transform


UNKNOWN = np.flatnonzero(ORDERS >= 4)
CANDIDATES = np.concatenate((MASKS[4], MASKS[5], MASKS[6], [255]))
DESIGN = SUBSETS[CANDIDATES][:, UNKNOWN].astype(float)
COSTS = np.array([4] * 70 + [16] * 56 + [64] * 28 + [10000])


def prior(terms, predicted=None, path_weight=0.0, independent=1.0, fifth_weight=1.0, scale_mode=0):
    triple_strength = SUBSETS[UNKNOWN][:, MASKS[3]] @ np.abs(terms[MASKS[3]])
    scales = triple_strength * (0.15 ** (ORDERS[UNKNOWN] - 3))
    if scale_mode:
        all_scales = np.abs(terms).copy()
        for mask in UNKNOWN:
            children = np.array([mask ^ (1 << orbital) for orbital in range(8) if mask & (1 << orbital)])
            values = np.sort(all_scales[children])
            if scale_mode == 1:
                strength = values[:-1].sum() * len(values) / (len(values) - 1)
            elif scale_mode == 2:
                strength = np.sqrt(values[-1] * values[:-1].sum())
            else:
                strength = 0
                for child in children:
                    added = mask ^ child
                    edges = np.array([added | (1 << orbital) for orbital in range(8) if child & (1 << orbital)])
                    activity = -terms[added] - sum(terms[1 << orbital] for orbital in range(8) if child & (1 << orbital))
                    strength += all_scales[child] * np.sqrt(np.sum(np.abs(terms[edges])) / max(activity, 1e-10)) / 0.15
            all_scales[mask] = strength * 0.15 / max(1, ORDERS[mask] - 3)
        scales = all_scales[UNKNOWN]
    scales[ORDERS[UNKNOWN] >= 5] *= fifth_weight
    covariance = np.diag((scales * independent) ** 2 + 1e-20)
    if path_weight:
        features = np.zeros((len(UNKNOWN), 28))
        for row, mask in enumerate(UNKNOWN):
            for column, pair in enumerate(MASKS[2]):
                if pair & mask == pair:
                    orbitals = [orbital for orbital in range(8) if pair & (1 << orbital)]
                    values = []
                    for orbital in orbitals:
                        child = mask ^ (1 << orbital)
                        if ORDERS[child] == 3:
                            values.append(terms[child])
                        elif predicted is not None:
                            values.append(predicted[child])
                    features[row, column] = sum(values)
        covariance += path_weight ** 2 * features @ features.T
    return covariance


def acquire(terms, covariance, mean=None, budget=104, power=1.0, return_queries=False, force_six=False, quints=None):
    means = np.zeros(len(CANDIDATES)) if mean is None else DESIGN @ mean[UNKNOWN]
    truth = DESIGN @ terms[UNKNOWN]
    kernel = DESIGN @ covariance @ DESIGN.T
    selected = []
    remaining = budget
    for step in range(26):
        variance = np.maximum(np.diag(kernel), 1e-30)
        scores = kernel[-1] ** 2 / variance / COSTS ** power
        scores[COSTS > remaining] = -1
        scores[selected] = -1
        if force_six and step == 0:
            scores[COSTS != 64] = -1
        if quints is not None:
            scores[COSTS != (16 if step < quints else 4)] = -1
        query = int(np.argmax(scores))
        if scores[query] <= 0:
            break
        remaining -= COSTS[query]
        selected.append(query)
        gain = kernel[:, query].copy() / variance[query]
        means += gain * (truth[query] - means[query])
        kernel -= np.outer(gain, kernel[query].copy())
    if return_queries:
        return CANDIDATES[selected], means[-1], budget - remaining
    return means[-1] - truth[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--path', type=float, default=0)
    parser.add_argument('--fifth', type=float, default=1)
    parser.add_argument('--power', type=float, default=1)
    parser.add_argument('--neural', type=float, default=0)
    parser.add_argument('--scale', type=int, default=0)
    arguments = parser.parse_args()
    data = np.load('train.npz')
    terms = transform(data['energies'][-1800:])[:arguments.count]
    families = data['families'][-1800:][:arguments.count]
    means = np.zeros_like(terms)
    if arguments.neural:
        for order in [4, 5]:
            prediction = np.load('neural_validation' + str(order) + '.npz')
            means[:, prediction['masks']] = prediction['predicted'][:arguments.count] * arguments.neural
    started = time.time()
    errors = []
    counts = np.zeros(3)
    for row, mean in zip(terms, means):
        covariance = prior(row, mean, path_weight=arguments.path, fifth_weight=arguments.fifth, scale_mode=arguments.scale)
        queries, estimate, cost = acquire(row, covariance, mean=mean, power=arguments.power, return_queries=True)
        for index, order in enumerate([4, 5, 6]):
            counts[index] += np.sum(ORDERS[queries] == order)
        errors.append(estimate - row[UNKNOWN].sum())
    report(np.array(errors), families, str(vars(arguments)))
    print('queries', counts / len(terms), 'seconds', time.time() - started, flush=True)


if __name__ == '__main__':
    main()

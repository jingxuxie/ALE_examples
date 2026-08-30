import argparse
from pathlib import Path

import numpy as np

from acquisition import UNKNOWN, acquire, prior
from experiment import ORDERS, report, transform


def load_predictions(count=1800):
    data = np.load('train.npz')
    terms = transform(data['energies'][-1800:])[:count]
    families = data['families'][-1800:][:count]
    means = np.zeros_like(terms)
    scales = np.sqrt(np.array([np.diag(prior(row)) for row in terms]))
    for order in [4, 5]:
        prediction = np.load('neural_validation' + str(order) + '.npz')
        means[:, prediction['masks']] = prediction['predicted'][:count]
        if Path('variance_validation' + str(order) + '.npz').is_file():
            prediction = np.load('variance_validation' + str(order) + '.npz')
            for column, mask in enumerate(prediction['masks']):
                scales[:, np.flatnonzero(UNKNOWN == mask)[0]] = prediction['predicted'][:count, column] * 2
        else:
            scales[:, ORDERS[UNKNOWN] == order] *= 0.1
    scales[:, ORDERS[UNKNOWN] >= 6] *= 0.05
    return terms, families, means, scales


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--power', type=float, default=.8)
    parser.add_argument('--fifth', type=float, default=1)
    parser.add_argument('--floor', type=float, default=0)
    parser.add_argument('--count', type=int, default=600)
    arguments = parser.parse_args()
    terms, families, means, scales = load_predictions(arguments.count)
    scales[:, ORDERS[UNKNOWN] >= 5] *= arguments.fifth
    errors = []
    for row, mean, scale, family in zip(terms, means, scales, families):
        if family in [0, 3, 4]:
            mean = mean * 0
        covariance = np.diag(scale ** 2 + arguments.floor ** 2 * np.diag(prior(row)))
        error = acquire(row, covariance, mean=mean, power=arguments.power)
        errors.append(error)
    report(np.array(errors), families, str(vars(arguments)))


if __name__ == '__main__':
    main()

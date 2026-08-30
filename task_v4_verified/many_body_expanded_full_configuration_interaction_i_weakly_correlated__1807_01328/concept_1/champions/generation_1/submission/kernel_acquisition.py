import argparse

import numpy as np

from acquisition import UNKNOWN, acquire, prior
from experiment import ORDERS, report
from neural import features
from variance_acquisition import load_predictions


def embeddings(inputs, order):
    weights = np.load('network' + str(order) + '.npz')
    values = inputs
    for index in [0, 2, 4]:
        values = values @ weights[str(index) + '_weight'].T + weights[str(index) + '_bias']
        values = values / (1 + np.exp(np.clip(-values, -60, 60)))
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weight', type=float, default=1)
    parser.add_argument('--rank', type=int, default=16)
    parser.add_argument('--power', type=float, default=.6)
    parser.add_argument('--count', type=int, default=600)
    arguments = parser.parse_args()
    data = np.load('train.npz')
    inputs, targets, output_scales, masks = features(data['energies'][-1800:][:arguments.count], data['orbitals'][-1800:][:arguments.count], data['families'][-1800:][:arguments.count])
    hidden = embeddings(inputs, 4)
    flat = hidden.reshape(-1, hidden.shape[-1])
    center = flat.mean(0)
    covariance = np.cov(flat, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    projection = eigenvectors[:, -arguments.rank:] / np.sqrt(eigenvalues[-arguments.rank:])[None, :]
    encoded = (hidden - center) @ projection
    encoded = np.concatenate((np.ones_like(encoded[:, :, :1]), encoded), axis=2)
    terms, families, means, scales = load_predictions(arguments.count)
    errors = []
    mapping = np.array([np.flatnonzero(UNKNOWN == mask)[0] for mask in masks])
    for index, (row, mean, scale, family) in enumerate(zip(terms, means, scales, families)):
        if family in [0, 3, 4]:
            mean = mean * 0
        factors = np.zeros((len(UNKNOWN), encoded.shape[-1]))
        factors[mapping] = encoded[index] * scale[mapping, None]
        covariance = np.diag(scale ** 2) + arguments.weight ** 2 / arguments.rank * factors @ factors.T
        errors.append(acquire(row, covariance, mean=mean, power=arguments.power))
    report(np.array(errors), families, str(vars(arguments)))


if __name__ == '__main__':
    main()

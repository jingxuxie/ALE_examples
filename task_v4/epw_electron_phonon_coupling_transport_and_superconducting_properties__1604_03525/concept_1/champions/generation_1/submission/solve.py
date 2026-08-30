import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import argparse
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def observation_features(inputs, mean, basis):
    omega_squared = inputs['omega_mev'] ** 2
    dimension = basis.shape[1]
    count = len(inputs['interaction'])
    result = np.empty((count, dimension + 40), dtype=np.float32)
    triangle = np.tril_indices(8)
    for row in range(count):
        slots = np.flatnonzero(inputs['mask'][row])
        kernel = omega_squared / (
            omega_squared + inputs['nu_mev'][row, slots, None] ** 2
        )
        coupling = max(float(inputs['interaction'][row, 0]), 1e-8)
        standard = inputs['noise_std'][row, slots] / coupling
        rho = inputs['noise_rho'][row]
        length = inputs['noise_length'][row]
        correlation = (1 - rho) * np.eye(len(slots)) + rho * np.exp(
            -np.abs(slots[:, None] - slots[None, :]) / length
        )
        covariance = standard[:, None] * correlation * standard[None, :]
        normalizer = np.eye(len(slots))
        normalizer[:, 0] -= kernel @ mean
        covariance = normalizer @ covariance @ normalizer.T
        covariance[0, 0] = 1
        design = kernel @ basis
        mapping = cho_solve(cho_factor(design @ design.T + covariance), design).T
        residual = inputs['interaction'][row, slots] / coupling - kernel @ mean
        result[row, :dimension] = mapping @ residual
        uncertainty = np.eye(dimension) - mapping @ design
        result[row, dimension:dimension + 36] = uncertainty[:8, :8][triangle]
        result[row, -4:] = [
            np.log(standard[0]), inputs['temperature_k'][row], rho, length
        ]
    return result


def monotone_cumulative(cumulative):
    output = np.clip(cumulative.astype(np.float64), 0, 1)
    output[:, -1] = 1
    size = output.shape[1]
    for row in range(len(output)):
        levels = np.empty(size)
        counts = np.empty(size, dtype=np.int64)
        blocks = 0
        for position in range(size):
            levels[blocks] = output[row, position]
            counts[blocks] = 1
            blocks += 1
            while blocks > 1 and levels[blocks - 2] > levels[blocks - 1]:
                total = counts[blocks - 2] + counts[blocks - 1]
                levels[blocks - 2] = (
                    levels[blocks - 2] * counts[blocks - 2]
                    + levels[blocks - 1] * counts[blocks - 1]
                ) / total
                counts[blocks - 2] = total
                blocks -= 1
        position = 0
        for block in range(blocks):
            endpoint = position + counts[block]
            output[row, position:endpoint] = levels[block]
            position = endpoint
    return output


def model_cumulative(features, assets, prefix):
    mean = np.asarray(assets[prefix + 'mean'], dtype=np.float64)
    basis = np.asarray(assets[prefix + 'basis'], dtype=np.float64)
    hidden = (features.astype(np.float64) - assets[prefix + 'xmean']) / assets[prefix + 'xstd']
    for layer in range(4):
        hidden = hidden @ assets[prefix + f'weight{layer}'].T
        hidden += assets[prefix + f'bias{layer}']
        if layer < 3:
            hidden = hidden / (1 + np.exp(np.clip(-hidden, -80, 80)))
    dimension = basis.shape[1]
    if str(assets[prefix + 'kind']) == 'pca':
        probability = mean + (features[:, :dimension] + hidden) @ basis.T
        cumulative = np.cumsum(probability, axis=1)
    else:
        probability = mean + features[:, :dimension] @ basis.T
        cumulative = np.cumsum(probability, axis=1) + .05 * hidden
    cumulative[:, -1] = 1
    return cumulative


def predict(inputs, assets, mean, basis):
    features = observation_features(inputs, mean, basis)
    cumulative = np.zeros((len(features), len(mean)), dtype=np.float64)
    for model_index, weight in enumerate(assets['weights']):
        if weight > 0:
            predicted = model_cumulative(features, assets, f'model{model_index}_')
            cumulative += weight * predicted
    cumulative /= np.sum(assets['weights'])
    cumulative = monotone_cumulative(cumulative)
    probability = np.maximum(np.diff(cumulative, axis=1, prepend=0), 0)
    probability /= probability.sum(axis=1, keepdims=True)
    coupling = np.maximum(inputs['interaction'][:, :1], 1e-8)
    return probability * coupling * inputs['omega_mev'] / (2 * inputs['domega_mev'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    directory = Path(__file__).resolve().parent
    with np.load(arguments.input, allow_pickle=False) as archive:
        inputs = dict(archive)
    with np.load(directory / 'prior.npz', allow_pickle=False) as archive:
        mean, basis = archive['mean'], archive['basis']
    with np.load(directory / 'ensemble.npz', allow_pickle=False) as archive:
        assets = dict(archive)
    prediction = predict(inputs, assets, mean, basis)
    np.savez_compressed(arguments.output, alpha2f=prediction)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.special import softmax
from model import Physics, InterpolatedPhysics, Fit
from network import predict_network, align_sheets
from sampling import posterior_mass


def predict(observed, sigma, omega, sheet_count):
    directory = Path(__file__).resolve().parent
    configuration = json.loads((directory / 'models.json').read_text())
    prediction = np.zeros((len(observed), 3, 14))
    three = sheet_count == 3
    if np.any(three):
        total = 0.
        for name, weight in configuration['networks']:
            current = predict_network(observed[three], sigma[three], directory / name)
            if total:
                current = align_sheets(prediction[three] / total, current)
            prediction[three] += weight * current
            total += weight
        prediction[three] /= total
    physics = InterpolatedPhysics(omega, 12, 20)
    target_physics = Physics(omega, 32)
    two_indices = np.flatnonzero(sheet_count == 2)
    budget = min(3.1, 145. / max(len(two_indices), 1))
    started = time.process_time()
    for index in two_indices:
        parameters = []
        results = []
        masses = []
        costs = []
        determinants = []
        for family in range(3):
            fitter = Fit(physics, observed[index], sigma[index], family, 3.)
            fitted, result = fitter.run(max_nfev=50)
            parameters.append(fitted)
            results.append(result)
            masses.append(target_physics.target(fitted, family))
            costs.append(2 * result.cost)
            determinants.append(np.linalg.slogdet(result.jac.T @ result.jac)[1])
        chosen = int(np.argmin(costs))
        if time.process_time() - started < 153.:
            digest = hashlib.blake2b(np.ascontiguousarray(observed[index]).tobytes(), digest_size=8).digest()
            seed = int.from_bytes(digest, 'little')
            masses[chosen] = posterior_mass(physics, target_physics, observed[index], sigma[index], chosen, parameters[chosen], results[chosen], seed, budget=budget)
        weights = softmax(-.5 * (np.array(costs) + np.array(determinants)))
        prediction[index] = np.einsum('n,nij->ij', weights, np.asarray(masses))
    prediction = np.maximum(prediction, 0)
    for index, bands in enumerate(sheet_count):
        prediction[index, bands:] = 0
        totals = prediction[index, :bands].sum(axis=1, keepdims=True)
        prediction[index, :bands] /= np.maximum(totals, 1e-300)
    return prediction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        prediction = predict(archive['observed'], archive['sigma'], archive['omega'], archive['sheet_count'])
    np.savez_compressed(arguments.output, spectral_mass=prediction)


if __name__ == '__main__':
    main()

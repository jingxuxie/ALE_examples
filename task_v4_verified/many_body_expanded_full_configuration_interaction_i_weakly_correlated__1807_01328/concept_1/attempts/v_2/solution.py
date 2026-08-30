import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from scipy.linalg import solve as linear_solve
from quadrature import ORDERS, SUBSET, HIGH, CANDIDATES, SELECTOR, TRIPLES, PAIR, SINGLE, mobius, features
from angle_fit import AngleFit
from response_fit import MASKS
from design import covariance, design, estimate

ROOT = Path(__file__).resolve().parent


def load_models():
    with np.load(ROOT / 'quadrature_model.npz') as archive:
        return archive['variance_scale'][ORDERS[HIGH] - 4]


def send(message):
    sys.stdout.write(json.dumps(message, separators=(',', ':'), allow_nan=False) + '\n')
    sys.stdout.flush()


def receive():
    line = sys.stdin.readline()
    return json.loads(line) if line else {'event': 'done'}


def request(masks, values, observed):
    send({'query': [int(mask) for mask in masks]})
    response = receive()
    for mask, value in response['values']:
        values[mask] = value
        observed.add(mask)


def solve(observation, variance_factors, system_index):
    values = np.zeros(256)
    observed = set()
    for mask, value in observation['values']:
        values[mask] = value
        observed.add(mask)
    requested = [int(mask) for mask in TRIPLES if mask not in observed]
    if requested:
        request(requested, values, observed)
    orbital = np.asarray(observation['orbital_energy'], dtype=float)
    weights = np.maximum(features(values)[1] * variance_factors, 1e-25)
    matrix = covariance(weights, .7, 8)
    chosen = design(matrix, 'anchor')
    masks = CANDIDATES[chosen]
    if len(masks):
        request(masks, values, observed)
    terms = mobius(values)
    terms[ORDERS > 3] = 0
    low = SUBSET @ terms
    truth = np.zeros(len(CANDIDATES) + 1)
    truth[chosen] = values[masks] - low[masks]
    mean = np.zeros(len(CANDIDATES) + 1)
    if chosen:
        correction = estimate(matrix, mean, truth, chosen)[0]
        gram = matrix[np.ix_(chosen, chosen)]
        gram = gram + np.eye(len(chosen)) * max(np.max(np.diag(gram)) * 1e-12, 1e-26)
        remaining_variance = matrix[-1, -1] - matrix[-1, chosen] @ linear_solve(gram, matrix[chosen, -1], assume_a='pos')
        available = 104.0 - time.process_time() - .08 * max(120 - system_index, 0)
        if remaining_variance > 4e-12 and available > .15:
            try:
                baseline_norm = max(truth[chosen] @ linear_solve(gram, truth[chosen], assume_a='pos'), 1e-20)
                candidates = []
                for canonical in [False, True]:
                    available = 104.0 - time.process_time() - .08 * max(120 - system_index, 0)
                    if available < .15:
                        break
                    if canonical and candidates and candidates[0][0] < .005 and candidates[0][1] < .03:
                        break
                    mapping = np.arange(256)
                    fitted_orbital = orbital.copy()
                    if canonical:
                        ordering = np.argsort(values[SINGLE])
                        mapping = (MASKS.astype(int) * (1 << ordering)[None]).sum(axis=1)
                        fitted_orbital[3:] = fitted_orbital[3:][ordering]
                    reverse = np.argsort(mapping)
                    fitted = AngleFit(values[mapping], fitted_orbital, reverse[np.r_[PAIR, TRIPLES, masks]])
                    response = fitted.fit(starts=5, iterations=250, time_budget=min(.8, available))[reverse]
                    if not np.all(np.isfinite(response)):
                        continue
                    response_mean = SELECTOR @ mobius(response)[HIGH]
                    residual = truth[chosen] - response_mean[chosen]
                    relative_error = (residual @ linear_solve(gram, residual, assume_a='pos')) / baseline_norm
                    candidate = estimate(matrix, response_mean, truth, chosen)[0]
                    candidates.append((fitted.score, relative_error, candidate))
                if candidates:
                    candidates.sort(key=lambda item: item[0])
                    best = candidates[0]
                    trusted = best[0] < .005 and best[1] < .25
                    if len(candidates) == 2:
                        alternate = candidates[1]
                        disagreement = abs(best[2] - alternate[2])
                        tolerance = max(5e-6, .15 * math.sqrt(max(remaining_variance, 0.0)))
                        if alternate[0] < 1.5 * best[0] and disagreement > tolerance:
                            trusted = False
                        if disagreement <= tolerance and max(best[1], alternate[1]) < .15:
                            trusted = True
                    if trusted:
                        correction = best[2]
            except (ValueError, ArithmeticError, np.linalg.LinAlgError):
                pass
    else:
        correction = float(mean[-1])
    predicted = float(low[-1] + correction)
    if not math.isfinite(predicted):
        predicted = float(low[-1])
    predicted = min(predicted, min(values[mask] for mask in observed))
    send({'estimate': predicted})


def main():
    models = load_models()
    system_index = 0
    while True:
        observation = receive()
        event = observation.get('event')
        if event == 'done':
            return
        if event == 'start':
            system_index += 1
            solve(observation, models, system_index)


if __name__ == '__main__':
    main()

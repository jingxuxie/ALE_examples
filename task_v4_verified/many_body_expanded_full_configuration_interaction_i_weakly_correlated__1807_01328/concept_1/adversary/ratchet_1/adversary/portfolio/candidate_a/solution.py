import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import json
import sys
import time
from pathlib import Path

import numpy as np

from acquisition import CANDIDATES, DESIGN, UNKNOWN, acquire, prior
from experiment import MASKS, ORDERS, SUBSETS, transform
from neural import features
from physical import Physical
from adaptive import adaptive_covariance, quiet_core


ROOT = Path(__file__).resolve().parent
FAMILIES = ('local', 'collective', 'frustrated', 'bridge', 'density', 'mixed')
NETWORKS = {order: dict(np.load(ROOT / ('network' + str(order) + '.npz'))) for order in (4, 5)}
STARTED = time.process_time()


def send(value):
    print(json.dumps(value, allow_nan=False), flush=True)


def receive():
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return json.loads(line)


def predict_prior(energy, orbitals, family):
    mean = np.zeros(256)
    if family in (0, 3, 4):
        return mean
    for order in (4, 5):
        inputs, _, scales, masks = features(energy[None, :], orbitals[None, :], np.array([family]), order)
        hidden = inputs[0]
        weights = NETWORKS[order]
        for index in (0, 2, 4, 6):
            hidden = hidden @ weights[str(index) + '_weight'].T + weights[str(index) + '_bias']
            if index != 6:
                hidden = hidden / (1 + np.exp(np.clip(-hidden, -60, 60)))
        mean[masks] = hidden[:, 0] * scales[0]
    return mean


def physical_tail(energy, orbitals, family, terms, queries, weights, fallback, uncertainty):
    if family not in (1, 2, 5) or time.process_time() - STARTED > 103:
        return fallback
    if uncertainty < 4e-6:
        return fallback
    observed = np.r_[np.flatnonzero((ORDERS >= 1) & (ORDERS <= 3)), queries]
    problem = Physical(energy, orbitals, observed=observed, density_scale=.15 if family == 5 else .07)
    problem.ridge = .01
    candidates = []
    local_start = time.process_time()
    result = problem.fit(0, iterations=240, init_mode='naive', scaling=1.0)
    candidates.append(result)
    score = np.linalg.norm(result.fun[:len(observed)])
    if score > .04 and time.process_time() - STARTED < 100:
        for seed in (1, 2, 3):
            if time.process_time() - local_start > 1.5:
                break
            candidate = problem.fit(seed, iterations=180, init_mode='quadratic', scaling=1.0)
            candidates.append(candidate)
            score = min(score, np.linalg.norm(candidate.fun[:len(observed)]))
            if score < .025:
                break
    best = min(candidates, key=lambda candidate: np.linalg.norm(candidate.fun[:len(observed)]))
    score = float(np.linalg.norm(best.fun[:len(observed)]))
    if score > .075 and uncertainty > 2e-5 and time.process_time() - STARTED < 90:
        starts = []
        for seed in range(32):
            if time.process_time() - STARTED > 98:
                break
            candidate = problem.fit(seed, iterations=30, init_mode='quadratic', scaling=1.0)
            starts.append(candidate)
        starts.sort(key=lambda candidate: np.linalg.norm(candidate.fun))
        for candidate in starts[:8]:
            if time.process_time() - STARTED > 100:
                break
            candidate = problem.fit(initial=candidate.x, iterations=180, scaling=1.0)
            candidate_score = float(np.linalg.norm(candidate.fun[:len(observed)]))
            if candidate_score < score:
                best = candidate
                score = candidate_score
            if score < .025:
                break
    if score < .15 and time.process_time() - STARTED < 102:
        problem.ridge = .001
        problem.cache_parameters = None
        refined = problem.fit(initial=best.x, iterations=220, scaling=1.0)
        refined_score = float(np.linalg.norm(refined.fun[:len(observed)]))
        if refined_score < score:
            best = refined
            score = refined_score
    if score > .075:
        return fallback
    fitted = problem.predict(best.x, np.r_[observed, 255])
    predicted = np.zeros(256)
    predicted[observed] = fitted[:-1]
    predicted[255] = fitted[-1]
    low = transform(predicted)
    low[ORDERS >= 4] = 0
    tails = predicted - SUBSETS @ low
    measured = energy[queries] - SUBSETS[queries] @ terms
    estimate = tails[255] + weights @ (measured - tails[queries])
    if not np.isfinite(estimate) or abs(estimate - fallback) > max(8e-5, uncertainty * 1.5):
        return fallback
    confidence = 1 / (1 + (score / .07) ** 4)
    return confidence * estimate + (1 - confidence) * fallback


def solve(observation):
    energy = np.zeros(256)
    for mask, value in observation['values']:
        energy[mask] = value
    orbitals = np.asarray(observation['orbital_energy'])
    family = FAMILIES.index(observation['family'])
    send({'query': MASKS[3].tolist()})
    response = receive()
    for mask, value in response['values']:
        energy[mask] = value
    terms = transform(energy)
    terms[ORDERS >= 4] = 0
    mean = predict_prior(energy, orbitals, family)
    omitted = quiet_core(terms) if family == 5 else None
    covariance = prior(terms, fifth_weight=2) if omitted is None else adaptive_covariance(terms, omitted)
    queries, _, _ = acquire(terms, covariance, mean=mean, budget=int(response['remaining']), power=.8,
                            return_queries=True, force_six=omitted is not None, quints=0 if omitted is None else None)
    print(json.dumps({'portfolio_queries': queries.tolist(), 'quiet_core_omitted': omitted,
                      'family': observation['family']}), file=sys.stderr, flush=True)
    send({'query': queries.tolist()})
    response = receive()
    for mask, value in response['values']:
        energy[mask] = value
    design = SUBSETS[queries][:, UNKNOWN].astype(float)
    kernel = design @ covariance @ design.T
    weights = np.linalg.solve(kernel + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
    measured = energy[queries] - SUBSETS[queries] @ terms
    tail = mean[UNKNOWN].sum() + weights @ (measured - design @ mean[UNKNOWN])
    uncertainty = np.sqrt(max(0, covariance.sum() - weights @ (design @ covariance @ np.ones(len(UNKNOWN)))))
    try:
        if omitted is None:
            tail = physical_tail(energy, orbitals, family, terms, queries, weights, tail, uncertainty)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        pass
    send({'estimate': float(terms.sum() + tail)})


def main():
    while True:
        try:
            observation = receive()
        except EOFError:
            return
        if observation['event'] == 'done':
            return
        if observation['event'] == 'start':
            solve(observation)


if __name__ == '__main__':
    main()

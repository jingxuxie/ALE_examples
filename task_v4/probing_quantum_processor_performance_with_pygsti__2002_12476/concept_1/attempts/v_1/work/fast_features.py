import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get('ASSETS', '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/probing_quantum_processor_performance_with_pygsti__2002_12476/concept_1/participant'))
sys.path.insert(0, str(ROOT / 'workspace'))
from physics import FAMILIES, PARAMETER_SCALES, fisher_features, sample_parameters

CANDIDATES = json.loads((ROOT / 'input/candidates.json').read_text())


def probabilities_fast(parameters):
    shape = parameters.shape[:-1]
    rotations = parameters[..., :9].reshape(*shape, 3, 3).copy()
    rotations[..., 0, 0] += np.pi / 2
    rotations[..., 1, 1] += np.pi / 2
    angles = np.linalg.norm(rotations, axis=-1)
    cross = np.zeros((*shape, 3, 3, 3))
    cross[..., 0, 1] = -rotations[..., 2]
    cross[..., 0, 2] = rotations[..., 1]
    cross[..., 1, 0] = rotations[..., 2]
    cross[..., 1, 2] = -rotations[..., 0]
    cross[..., 2, 0] = -rotations[..., 1]
    cross[..., 2, 1] = rotations[..., 0]
    first = np.sinc(angles / np.pi)
    second = 0.5 * np.sinc(angles / (2 * np.pi)) ** 2
    gates = (np.eye(3) + first[..., None, None] * cross +
             second[..., None, None] * (cross @ cross))
    gates *= np.exp(-parameters[..., 9:12])[..., None, None]
    gate_map = {label: gates[..., index, :, :] for index, label in enumerate('XYI')}
    products = {}
    powers = {}
    result = np.empty((*shape, len(CANDIDATES)))
    for index, circuit in enumerate(CANDIDATES):
        germ = circuit['germ']
        repetitions = circuit['repetitions']
        if germ not in products:
            product = np.eye(3)
            for label in germ:
                product = gate_map[label] @ product
            products[germ] = product
        key = germ, repetitions
        if key not in powers:
            powers[key] = np.linalg.matrix_power(products[germ], repetitions)
        preparation = circuit['preparation']
        expectation = powers[key][..., circuit['measurement'], preparation // 2]
        expectation = expectation * (1 if preparation % 2 == 0 else -1)
        result[..., index] = (1 + parameters[..., 12] + parameters[..., 13] * expectation) / 2
    return result


def features_fast(parameters, step=1e-6):
    parameters = np.atleast_2d(parameters)
    perturbations = np.concatenate([np.zeros((1, 14)), np.eye(14) * step, -np.eye(14) * step])
    probabilities = probabilities_fast(parameters[:, None, :] + perturbations[None, :, :])
    base = probabilities[:, 0]
    derivatives = (probabilities[:, 1:15] - probabilities[:, 15:29]).transpose(0, 2, 1) / (2 * step)
    return derivatives * PARAMETER_SCALES / np.sqrt(base * (1 - base))[..., None]


def generate(count, seed, filename):
    generator = np.random.default_rng(seed)
    parameters = np.array([sample_parameters(generator, family) for family in FAMILIES for _ in range(count)])
    families = np.repeat(FAMILIES, count)
    started = time.time()
    features = np.concatenate([features_fast(parameters[start:start + 12]) for start in range(0, len(parameters), 12)])
    np.savez(filename, features=features, parameters=parameters, families=families)
    print(filename, features.shape, 'seconds', time.time() - started, flush=True)


if __name__ == '__main__':
    parameters = sample_parameters(np.random.default_rng(23), 'mixed')
    exact = fisher_features(parameters, CANDIDATES)
    fast = features_fast(parameters)[0]
    print('maximum feature discrepancy', np.max(np.abs(exact - fast)), flush=True)
    assert np.allclose(exact, fast, rtol=2e-5, atol=2e-8)
    generate(20, 381974, 'training.npz')
    generate(60, 712067, 'validation.npz')

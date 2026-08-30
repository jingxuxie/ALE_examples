import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import expm

PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/the_alf_algorithms_for_lattice_fermions_project_release_2_0_documentat__2012_11914/concept_1/participant')
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from physics import load_model, kinetic_matrix, weight_batch

OUTPUT = Path(__file__).resolve().parent
MODEL = load_model()
DELTA = MODEL['beta'] / MODEL['time_slices']
COUPLING = np.arccosh(np.exp(DELTA * MODEL['interaction'] / 2))
KINETIC = expm(-DELTA * kinetic_matrix())


def evaluate(fields):
    products = np.broadcast_to(np.eye(16), (len(fields), 16, 16)).copy()
    for time_index in range(16):
        diagonal = np.exp(COUPLING * fields[:, time_index, :])
        products = KINETIC @ (diagonal[..., :, None] * products)
    eigenvalues = np.linalg.eigvals(products)
    distance = np.abs(eigenvalues + 1) / (1 + np.abs(eigenvalues))
    score = distance.min(axis=1)
    fugacity = np.exp(MODEL['beta'] * MODEL['chemical_potential'])
    signs = np.linalg.slogdet(products + np.eye(16) * fugacity)[0]
    signs *= np.linalg.slogdet(products + np.eye(16) / fugacity)[0]
    return score, signs


def save_candidate(fields, name='witness.json'):
    (OUTPUT / name).write_text(json.dumps({'fields': fields.tolist()}) + '\n')


def check_negative(fields):
    for candidate in fields:
        results = [weight_batch(candidate, MODEL, point)[0][0] for point in MODEL['certification_points']]
        if all(sign < 0 for sign in results):
            save_candidate(candidate)
            print('FOUND', results, flush=True)
            return True
    return False


def main():
    random = np.random.default_rng(908174)
    walkers = 128
    start = time.monotonic()
    best = 1.0
    for restart in range(30):
        fields = random.choice(np.array([-1, 1], dtype=np.int8), size=(walkers, 16, 16))
        if restart and (OUTPUT / 'best.json').exists():
            saved = np.array(json.loads((OUTPUT / 'best.json').read_text())['fields'], dtype=np.int8)
            fields[:walkers // 2] = saved
            mutation = random.random((walkers // 2, 16, 16)) < 0.1
            fields[:walkers // 2][mutation] *= -1
        scores, signs = evaluate(fields)
        for iteration in range(3000):
            candidates = fields.copy()
            count = random.choice([1, 2, 4, 8, 16], p=[0.60, 0.20, 0.12, 0.06, 0.02])
            for mutation_index in range(count):
                positions = random.integers(256, size=walkers)
                candidates.reshape(walkers, 256)[np.arange(walkers), positions] *= -1
            proposed, signs = evaluate(candidates)
            if np.any(signs < 0) and check_negative(candidates[signs < 0]):
                print('Elapsed', time.monotonic() - start, flush=True)
                return
            minimum = float(proposed.min())
            if minimum < best - 0.005:
                best = minimum
                save_candidate(candidates[np.argmin(proposed)], 'best.json')
                print('Best', best, 'restart', restart, 'iteration', iteration, 'seconds', round(time.monotonic() - start, 1), flush=True)
            temperatures = np.geomspace(0.0003, 0.03, walkers)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            fields[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 100 == 99:
                elite = np.argsort(scores)[:8]
                destinations = random.choice(walkers, 8, replace=False)
                fields[destinations] = fields[elite]
                scores[destinations] = scores[elite]
            if iteration % 500 == 0:
                print('Progress', restart, iteration, 'minimum', float(scores.min()), 'seconds', round(time.monotonic() - start, 1), flush=True)


if __name__ == '__main__':
    main()

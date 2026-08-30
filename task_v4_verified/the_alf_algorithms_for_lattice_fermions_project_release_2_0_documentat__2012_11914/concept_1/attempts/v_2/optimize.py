import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parents[1] / 'participant'
MODEL = json.loads((PARTICIPANT / 'input/model.json').read_text())
KINETIC_MATRIX = np.zeros((16, 16))
for horizontal in range(4):
    for vertical in range(4):
        source = 4 * horizontal + vertical
        for delta_horizontal, delta_vertical in [(1, 0), (0, 1)]:
            target = 4 * ((horizontal + delta_horizontal) % 4) + (vertical + delta_vertical) % 4
            KINETIC_MATRIX[source, target] = KINETIC_MATRIX[target, source] = -1


def evaluate(fields, multiplier=1, shift=0):
    beta = MODEL['beta'] * multiplier
    chemical = MODEL['chemical_potential'] + shift
    delta = beta / 16
    coupling = np.arccosh(np.exp(delta * 2))
    kinetic = expm(-delta * KINETIC_MATRIX)
    products = np.broadcast_to(np.eye(16), (len(fields), 16, 16)).copy()
    diagonals = np.exp(coupling * fields)
    for time_index in range(16):
        products = kinetic @ (diagonals[:, time_index, :, None] * products)
    eigenvalues = np.linalg.eigvals(products)
    if os.environ.get('OBJECTIVE') == 'phase':
        fugacity = np.exp(beta * chemical)
        distance = np.stack([np.prod((eigenvalues + target) / (np.abs(eigenvalues) + target), axis=1).real for target in [fugacity, 1 / fugacity]], axis=1)
    elif os.environ.get('OBJECTIVE') == 'target':
        fugacity = np.exp(beta * chemical)
        distance = np.minimum(np.abs(eigenvalues + fugacity) / (fugacity + np.abs(eigenvalues)), np.abs(eigenvalues + 1 / fugacity) / (1 / fugacity + np.abs(eigenvalues)))
    elif os.environ.get('OBJECTIVE') == 'angle':
        radius = np.abs(eigenvalues)
        distance = np.sqrt(np.maximum(0, (1 + eigenvalues.real / radius) / 2)) + 0.02 * np.abs(np.log(radius))
    else:
        distance = np.abs(eigenvalues + 1) / (1 + np.abs(eigenvalues))
    scores = distance.min(axis=1)
    fugacity = np.exp(beta * chemical)
    signs = np.linalg.slogdet(products + np.eye(16) * fugacity)[0]
    signs *= np.linalg.slogdet(products + np.eye(16) / fugacity)[0]
    return scores, signs


def save(fields, name):
    (ROOT / name).write_text(json.dumps({'fields': fields.tolist()}) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=45212)
    parser.add_argument('--walkers', type=int, default=128)
    parser.add_argument('--seconds', type=int, default=3000)
    parser.add_argument('--mode', type=int, default=0)
    parser.add_argument('--start', default='')
    args = parser.parse_args()
    random = np.random.default_rng(args.seed)
    walkers = args.walkers
    started = time.monotonic()
    champion = np.array(json.loads((PARTICIPANT / 'baseline/champion_witness.json').read_text())['fields'], dtype=np.int8)
    if args.start:
        champion = np.array(json.loads((ROOT / args.start).read_text())['fields'], dtype=np.int8)
    best = float(evaluate(champion[None])[0][0])
    best_field = champion.copy()
    save(best_field, f'best_{args.seed}.json')
    print('Initial', best, flush=True)
    for restart in range(100):
        fields = random.choice(np.array([-1, 1], dtype=np.int8), size=(walkers, 16, 16))
        fields[:walkers * 3 // 4] = best_field
        mutation = random.random(fields[:walkers * 3 // 4].shape) < random.uniform(0.01, 0.15, size=(walkers * 3 // 4, 1, 1))
        fields[:walkers * 3 // 4][mutation] *= -1
        fields[0] = best_field
        scores, signs = evaluate(fields)
        temperatures = np.geomspace(0.00005, 0.025, walkers)
        for iteration in range(4000):
            candidates = fields.copy()
            count = random.choice([1, 2, 4, 8, 16], p=[0.65, 0.20, 0.10, 0.04, 0.01])
            mutation_type = random.random()
            if args.mode == 2 and mutation_type > 0.75:
                sites = random.integers(4, size=walkers)
                time_index = random.integers(16, size=walkers)
                length = random.integers(1, 6)
                for offset in range(length):
                    for horizontal_offset in [0, 2]:
                        for vertical_offset in [0, 2]:
                            positions = (sites // 2 + horizontal_offset) * 4 + sites % 2 + vertical_offset
                            candidates[np.arange(walkers), (time_index + offset) % 16, positions] *= -1
            elif args.mode and mutation_type < 0.15:
                sites = random.integers(16, size=walkers)
                offsets = random.choice([-3, -2, -1, 1, 2, 3], size=walkers)
                for walker in range(walkers):
                    candidates[walker, :, sites[walker]] = np.roll(candidates[walker, :, sites[walker]], offsets[walker])
            elif args.mode and mutation_type < 0.35:
                time_index = random.integers(16, size=walkers)
                sites = random.integers(16, size=walkers)
                length = random.integers(2, 8)
                for offset in range(length):
                    candidates[np.arange(walkers), (time_index + offset) % 16, sites] *= -1
            else:
                for mutation_index in range(count):
                    positions = random.integers(256, size=walkers)
                    candidates.reshape(walkers, 256)[np.arange(walkers), positions] *= -1
            proposed, signs = evaluate(candidates)
            for candidate in candidates[signs < 0]:
                if all(evaluate(candidate[None], point['beta_multiplier'], point['chemical_shift'])[1][0] < 0 for point in MODEL['certification_points']):
                    save(candidate, f'found_{args.seed}.json')
                    save(candidate, 'witness.json')
                    print('FOUND', time.monotonic() - started, flush=True)
                    return
            minimum = float(proposed.min())
            if minimum < best:
                best = minimum
                best_field = candidates[np.argmin(proposed)].copy()
                save(best_field, f'best_{args.seed}.json')
                print('Best', best, restart, iteration, 'seconds', round(time.monotonic() - started, 1), flush=True)
            accepted = (proposed < scores) | (random.random(walkers) < np.exp(np.minimum(0, (scores - proposed) / temperatures)))
            fields[accepted] = candidates[accepted]
            scores[accepted] = proposed[accepted]
            if iteration % 100 == 99:
                elite = np.argsort(scores)[:8]
                destinations = random.choice(walkers, 8, replace=False)
                fields[destinations] = fields[elite]
                scores[destinations] = scores[elite]
            if iteration % 500 == 0:
                print('Progress', restart, iteration, float(scores.min()), round(time.monotonic() - started, 1), flush=True)
            if time.monotonic() - started > args.seconds:
                return


if __name__ == '__main__':
    main()

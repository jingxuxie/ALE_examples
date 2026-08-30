import argparse
import ctypes
import itertools
import json
import math
import time
import numpy as np
from beam import Problem, load_cases, Excitation, library, integer_array, double_array

library.replacements.argtypes = [ctypes.c_int] * 3 + [integer_array, integer_array, double_array, integer_array, double_array, double_array, ctypes.c_int, integer_array, double_array, double_array]


def run(filename, seconds=600):
    problem = Problem(load_cases()[1])
    record = json.load(open(filename))
    original_labels = [problem.gates.index(Excitation(tuple(entry['annihilate']), tuple(entry['create']))) for entry in record['gates']]
    original_angles = [entry['theta'] for entry in record['gates']]
    best = 1.0
    started = time.time()
    pool = []
    rng = np.random.default_rng(2048)

    def update(value, labels, angles):
        nonlocal best
        if value < best:
            best = value
            problem.save(list(reversed(list(zip(labels, angles)))), 'sector_10_4_best.json')
            submission = json.load(open('submission.json'))
            submission['circuits'][1] = json.load(open('sector_10_4_best.json'))
            with open('submission.json', 'w') as handle:
                json.dump(submission, handle, indent=2)
            print('BEST', value, 'seconds', time.time() - started, flush=True)

    removed_count = len(original_labels) - problem.case.max_gates
    for removed in itertools.combinations(range(len(original_labels)), removed_count):
        labels = [label for position, label in enumerate(original_labels) if position not in removed]
        angles = [angle for position, angle in enumerate(original_angles) if position not in removed]
        value, angles, state = problem.fit(labels, angles, iterations=120)
        pool.append((value, labels, angles))
        update(value, labels, angles)
        if value < 1e-11:
            return
    pool.sort(key=lambda entry: entry[0])
    pool = pool[:20]
    print('PRUNING DONE', len(pool), time.time() - started, flush=True)
    current = pool[0]
    scanned = set()
    iteration = 0
    while time.time() - started < seconds:
        value, labels, angles = current
        length = len(labels)
        scores = np.zeros((length, len(problem.gates), 2))
        library.replacements(problem.dimension, len(problem.gates), problem.stride, problem.sources, problem.destinations, problem.signs, problem.counts, problem.reference, problem.target, length, np.asarray(labels, dtype=np.int32), np.asarray(angles, dtype=float), scores)
        for position, label in enumerate(labels):
            scores[position, label, 0] = 100.0
        proposals = []
        for flat_index in np.argsort(scores[:, :, 0], axis=None)[:60]:
            position, label = np.unravel_index(flat_index, scores.shape[:2])
            trial_labels = list(labels)
            trial_angles = np.asarray(angles).copy()
            trial_labels[position] = int(label)
            trial_angles[position] = scores[position, label, 1]
            proposals.append((trial_labels, trial_angles))
        for position in range(length - 1):
            trial_labels = list(labels)
            trial_angles = np.asarray(angles).copy()
            trial_labels[position], trial_labels[position + 1] = trial_labels[position + 1], trial_labels[position]
            trial_angles[position], trial_angles[position + 1] = trial_angles[position + 1], trial_angles[position]
            proposals.append((trial_labels, trial_angles))
        for repeat in range(25):
            source, destination = rng.choice(length, 2, replace=False)
            trial_labels = list(labels)
            trial_angles = list(angles)
            trial_labels.insert(destination, trial_labels.pop(source))
            trial_angles.insert(destination, trial_angles.pop(source))
            proposals.append((trial_labels, trial_angles))
        outcomes = []
        for trial_labels, trial_angles in proposals:
            signature = tuple(trial_labels)
            if signature in scanned:
                continue
            scanned.add(signature)
            new_value, fitted, state = problem.fit(trial_labels, trial_angles, iterations=100)
            outcomes.append((new_value, trial_labels, fitted))
            update(new_value, trial_labels, fitted)
            if new_value < 1e-11:
                return
        if outcomes:
            outcomes.sort(key=lambda entry: entry[0])
            pool.extend(outcomes[:3])
            pool.sort(key=lambda entry: entry[0])
            pool = pool[:30]
            if outcomes[0][0] < value - 1e-10:
                current = outcomes[0]
            elif rng.random() < 0.5:
                current = outcomes[rng.integers(min(8, len(outcomes)))]
            else:
                current = pool[rng.integers(len(pool))]
        else:
            current = pool[rng.integers(len(pool))]
            scanned.clear()
        iteration += 1
        print('ROUND', iteration, 'current', current[0], 'best', best, 'seconds', time.time() - started, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('--seconds', type=int, default=600)
    arguments = parser.parse_args()
    run(arguments.filename, arguments.seconds)

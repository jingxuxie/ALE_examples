import argparse
import ctypes
import itertools
import json
import os
import time
import numpy as np
from beam import Problem, load_cases, Excitation, library, integer_array, double_array

library.insertions.argtypes = [ctypes.c_int] * 3 + [integer_array, integer_array, double_array, integer_array, double_array, double_array, ctypes.c_int, integer_array, double_array, double_array]


def run(filename, seconds, size, trials):
    problem = Problem(load_cases()[1])
    record = json.load(open(filename))
    labels = [problem.gates.index(Excitation(tuple(entry['annihilate']), tuple(entry['create']))) for entry in record['gates']]
    angles = [entry['theta'] for entry in record['gates']]
    value, angles, state = problem.fit(labels, angles, iterations=200)
    best = value
    current = (value, labels, angles)
    pool = [current]
    seen = set()
    rng = np.random.default_rng(581)
    started = time.time()
    iteration = 0

    def update(value, labels, angles):
        nonlocal best
        if value < best - 1e-13:
            best = value
            problem.save(list(reversed(list(zip(labels, angles)))), 'sector_10_4_grow.json')
            submission = json.load(open('submission.json'))
            submission['circuits'][1] = json.load(open('sector_10_4_grow.json'))
            with open('submission_new.json', 'w') as handle:
                json.dump(submission, handle, indent=2)
            os.replace('submission_new.json', 'submission.json')
            print('BEST', value, 'seconds', time.time() - started, flush=True)

    while time.time() - started < seconds:
        value, labels, angles = current
        expanded = [(value, labels, angles)]
        for growth in range(size):
            choices = []
            for value, current_labels, current_angles in expanded:
                length = len(current_labels)
                scores = np.zeros((length + 1, len(problem.gates), 2))
                library.insertions(problem.dimension, len(problem.gates), problem.stride, problem.sources, problem.destinations, problem.signs, problem.counts, problem.reference, problem.target, length, np.asarray(current_labels, dtype=np.int32), np.asarray(current_angles, dtype=float), scores)
                for flat_index in np.argsort(scores[:, :, 0], axis=None)[:trials]:
                    position, label = np.unravel_index(flat_index, scores.shape[:2])
                    new_labels = list(current_labels)
                    new_angles = list(current_angles)
                    new_labels.insert(position, int(label))
                    new_angles.insert(position, scores[position, label, 1])
                    signature = tuple(new_labels)
                    if signature in seen:
                        continue
                    seen.add(signature)
                    new_value, fitted, state = problem.fit(new_labels, new_angles, iterations=100)
                    choices.append((new_value, new_labels, fitted))
            choices.sort(key=lambda entry: entry[0])
            expanded = choices[:12]
            if not expanded:
                break
        outcomes = []
        for expanded_value, expanded_labels, expanded_angles in expanded:
            removed_count = len(expanded_labels) - problem.case.max_gates
            for removed in itertools.combinations(range(len(expanded_labels)), removed_count):
                new_labels = [label for position, label in enumerate(expanded_labels) if position not in removed]
                new_angles = [angle for position, angle in enumerate(expanded_angles) if position not in removed]
                signature = tuple(new_labels)
                if signature in seen:
                    continue
                seen.add(signature)
                new_value, fitted, state = problem.fit(new_labels, new_angles, iterations=100)
                outcomes.append((new_value, new_labels, fitted))
                update(new_value, new_labels, fitted)
                if new_value < 1e-11:
                    return
        outcomes.sort(key=lambda entry: entry[0])
        if outcomes:
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
            if iteration % 20 == 0:
                seen.clear()
        iteration += 1
        print('ROUND', iteration, 'current', current[0], 'best', best, 'expanded', expanded[0][0] if expanded else None, 'seconds', time.time() - started, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--size', type=int, default=1)
    parser.add_argument('--trials', type=int, default=60)
    arguments = parser.parse_args()
    run(arguments.filename, arguments.seconds, arguments.size, arguments.trials)

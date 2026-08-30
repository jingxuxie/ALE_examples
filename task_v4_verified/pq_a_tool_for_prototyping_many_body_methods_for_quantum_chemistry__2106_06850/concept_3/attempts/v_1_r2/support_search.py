import argparse
import math
import time
import numpy as np
from beam import Problem, load_cases


def search(problem, target, suffix, width=150):
    active = abs(target) > 1e-9
    candidates = []
    for label, (sources, destinations, signs) in enumerate(problem.pairs):
        both = active[sources] & active[destinations]
        if np.any(both):
            candidates.append((label, sources, destinations, signs))
    beam = []
    for reference_index in np.flatnonzero(active):
        reference = np.zeros(problem.dimension)
        reference[reference_index] = 1.0
        beam.append((1.0 - target[reference_index] ** 2, reference_index, [], [], reference))
    limit = problem.case.max_gates - len(suffix)
    started = time.time()
    for depth in range(limit):
        children = []
        seen = set()
        for error, reference_index, labels, angles, state in beam:
            reference = np.zeros(problem.dimension)
            reference[reference_index] = 1.0
            occupied = abs(state) > 1e-9
            for label, sources, destinations, signs in candidates:
                if labels and labels[-1] == label:
                    continue
                after = occupied.copy()
                after[sources] |= occupied[destinations]
                after[destinations] |= occupied[sources]
                if np.any(after & ~active) or not np.any(occupied[sources] | occupied[destinations]):
                    continue
                weight = float(target[sources] @ state[sources] + target[destinations] @ state[destinations])
                tangent = float(target[destinations] @ (signs * state[sources]) - target[sources] @ (signs * state[destinations]))
                constant = float(target @ state) - weight
                angle = math.atan2(tangent, weight) + (math.pi if constant < 0 else 0)
                new_labels = labels + [label]
                new_angles = list(angles) + [angle]
                value, fitted, trial = problem.fit(new_labels, new_angles, target, reference, iterations=45)
                oriented = trial * (1 if trial[np.argmax(abs(trial))] >= 0 else -1)
                key_array = np.round(oriented, 7)
                key_array[key_array == 0.0] = 0.0
                key = key_array.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                children.append((value, reference_index, new_labels, fitted, trial))
                if value < 1e-10:
                    path = suffix + list(reversed(list(zip(new_labels, fitted))))
                    mask = int(problem.masks[reference_index])
                    rebased = problem.rebase(path, mask)
                    if rebased is None:
                        bridge = problem.bridge(mask)
                        if len(path) + len(bridge) > problem.case.max_gates:
                            continue
                        rebased = path + bridge
                    problem.save(rebased, f'{problem.case.case_id}_support.json')
                    print('SOLVED', value, len(path), 'seconds', time.time() - started, flush=True)
                    return True
        children.sort(key=lambda entry: entry[0])
        beam = children[:width]
        print('FORWARD', depth + 1, 'best', beam[0][0] if beam else None, 'children', len(children), 'seconds', round(time.time() - started, 2), flush=True)
        if not beam:
            break
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint')
    parser.add_argument('--parents', type=int, default=5)
    parser.add_argument('--width', type=int, default=150)
    arguments = parser.parse_args()
    problem = Problem(load_cases()[1])
    data = np.load(arguments.checkpoint)
    for parent, (target, path) in enumerate(zip(data['states'][:arguments.parents], data['paths'][:arguments.parents])):
        suffix = [(int(label), float(angle)) for label, angle in path]
        print('PARENT', parent, 'support', np.count_nonzero(abs(target) > 1e-9), flush=True)
        if search(problem, target, suffix, arguments.width):
            break

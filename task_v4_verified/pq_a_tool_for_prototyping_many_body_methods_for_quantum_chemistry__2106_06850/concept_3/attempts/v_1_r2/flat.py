import argparse
import itertools
import time
import numpy as np
from beam import Problem, load_cases, apply_rotation


def two_step(problem, state, minimum=2):
    state = state.copy()
    state[abs(state) < 1e-10] = 0.0
    support = np.count_nonzero(state)
    flat = []
    seconds = []
    for label, (sources, destinations, signs) in enumerate(problem.pairs):
        first, second = state[sources] != 0.0, state[destinations] != 0.0
        both = np.flatnonzero(first & second)
        singles = np.count_nonzero(first ^ second)
        if len(both) and not singles:
            flat.append(label)
        if len(both) - singles >= minimum:
            seconds.append((label, both))
    children = []
    for first_label in flat:
        sources, destinations, signs = problem.pairs[first_label]
        coefficients = np.zeros((problem.dimension, 3))
        coefficients[:, 0] = state
        coefficients[:, 2] = state
        coefficients[sources, 2] = -state[sources]
        coefficients[destinations, 2] = -state[destinations]
        coefficients[sources, 1] = 2 * signs * state[destinations]
        coefficients[destinations, 1] = -2 * signs * state[sources]
        angles = []
        for second_label, active in seconds:
            if first_label == second_label:
                continue
            next_sources, next_destinations, next_signs = problem.pairs[second_label]
            for left, right in itertools.combinations(active, 2):
                first_source = coefficients[next_sources[left]]
                first_destination = next_signs[left] * coefficients[next_destinations[left]]
                second_source = coefficients[next_sources[right]]
                second_destination = next_signs[right] * coefficients[next_destinations[right]]
                polynomials = (np.convolve(first_source, second_destination) - np.convolve(first_destination, second_source), np.convolve(first_source, second_source) + np.convolve(first_destination, second_destination))
                for polynomial in polynomials:
                    scale = np.max(abs(polynomial))
                    if scale < 1e-11:
                        continue
                    polynomial[abs(polynomial) < scale * 1e-12] = 0.0
                    roots = np.roots(np.trim_zeros(polynomial, 'b')[::-1])
                    for root in roots:
                        if abs(root.imag) < 1e-8:
                            theta = 2 * np.arctan(root.real)
                            if abs(np.sin(2 * theta)) > 1e-7:
                                angles.append(float(theta))
        angles.sort()
        unique = []
        for angle in angles:
            if not unique or angle - unique[-1] > 1e-7:
                unique.append(angle)
        for first_angle in unique:
            intermediate = apply_rotation(state, problem.pairs[first_label], -first_angle)
            if np.count_nonzero(abs(intermediate) > 1e-9) != support:
                continue
            options = problem.candidates(intermediate, minimum)
            for second_label, second_angle, remaining, norm in options:
                second_label = int(second_label)
                trial = apply_rotation(intermediate, problem.pairs[second_label], -second_angle)
                children.append((remaining, norm, trial, [(first_label, first_angle), (second_label, float(second_angle))]))
    return children


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint')
    parser.add_argument('--parents', type=int, default=10)
    parser.add_argument('--minimum', type=int, default=3)
    parser.add_argument('--output', default='flat_candidates.npz')
    arguments = parser.parse_args()
    problem = Problem(load_cases()[1])
    data = np.load(arguments.checkpoint)
    candidates = []
    started = time.time()
    for parent, (state, path) in enumerate(zip(data['states'][:arguments.parents], data['paths'][:arguments.parents])):
        children = two_step(problem, state, arguments.minimum)
        for support, norm, trial, added in children:
            candidates.append((support, norm, trial, list(path) + added))
        print('PARENT', parent, 'support', np.count_nonzero(abs(state) > 1e-9), 'children', len(children), 'best', min((entry[0] for entry in children), default=None), 'seconds', time.time() - started, flush=True)
    candidates.sort(key=lambda entry: entry[:2])
    unique = []
    seen = set()
    for support, norm, state, path in candidates:
        key = problem.canonical(state)
        if key in seen:
            continue
        seen.add(key)
        unique.append((state, path))
    np.savez(arguments.output, states=np.array([entry[0] for entry in unique]), paths=np.array([entry[1] for entry in unique]))
    print('SAVED', len(unique), arguments.output, flush=True)


if __name__ == '__main__':
    main()

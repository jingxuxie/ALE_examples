import os
import sys
import json
import math
import time
import ctypes
import argparse
import numpy as np
from scipy.optimize import minimize, least_squares

sys.path.insert(0, os.environ['P'] + '/workspace')
from fermion import Excitation, load_cases, allowed_excitations, rotation_pairs, apply_rotation

library = ctypes.CDLL(os.path.join(os.path.dirname(__file__), 'search.so'))
integer_array = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
double_array = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
library.cancellations.argtypes = [ctypes.c_int] * 3 + [integer_array, integer_array, double_array, integer_array, double_array, ctypes.c_int, double_array]
library.cancellations.restype = ctypes.c_int
library.objective.argtypes = [ctypes.c_int] * 2 + [integer_array, integer_array, double_array, integer_array, double_array, double_array, ctypes.c_int, integer_array, double_array, double_array, double_array]
library.objective.restype = ctypes.c_double
library.canonical.argtypes = [ctypes.c_int, ctypes.c_int, integer_array, double_array, double_array]
library.circuit_jacobian.argtypes = [ctypes.c_int] * 2 + [integer_array, integer_array, double_array, integer_array, double_array, ctypes.c_int, integer_array, double_array, double_array, double_array]


class Problem:
    def __init__(self, case):
        self.case = case
        self.gates = allowed_excitations(case.n_orbitals)
        self.indices = np.array([index for index, mask in enumerate(case.determinants) if sum((mask >> orbital) & 1 for orbital in range(0, case.n_orbitals, 2)) == case.n_alpha])
        inverse = {index: position for position, index in enumerate(self.indices)}
        self.pairs = []
        for gate in self.gates:
            sources, destinations, signs = rotation_pairs(case.n_orbitals, case.n_electrons, gate)
            active = np.isin(sources, self.indices)
            self.pairs.append((np.array([inverse[index] for index in sources[active]], dtype=np.int32), np.array([inverse[index] for index in destinations[active]], dtype=np.int32), signs[active].copy()))
        self.stride = max(len(pairs[0]) for pairs in self.pairs)
        self.sources = np.zeros((len(self.gates), self.stride), dtype=np.int32)
        self.destinations = np.zeros_like(self.sources)
        self.signs = np.zeros(self.sources.shape)
        self.counts = np.array([len(pairs[0]) for pairs in self.pairs], dtype=np.int32)
        for label, (sources, destinations, signs) in enumerate(self.pairs):
            self.sources[label, :len(sources)] = sources
            self.destinations[label, :len(sources)] = destinations
            self.signs[label, :len(sources)] = signs
        self.target = case.target[self.indices].copy()
        self.dimension = len(self.target)
        self.reference_index = inverse[case.determinants.index(case.reference_mask)]
        self.reference = np.zeros(self.dimension)
        self.reference[self.reference_index] = 1.0
        self.buffer = np.zeros((4 * len(self.gates) * self.stride, 4))
        self.distance = np.array([(case.determinants[index] ^ case.reference_mask).bit_count() / 2 for index in self.indices])
        self.masks = np.array([case.determinants[index] for index in self.indices], dtype=np.int32)

    def canonical(self, state):
        output = np.zeros(self.dimension)
        library.canonical(self.case.n_orbitals, self.dimension, self.masks, state, output)
        output = np.round(output, 8)
        output[output == 0.0] = 0.0
        return output.tobytes()

    def phase_key(self, state):
        output = np.zeros(self.dimension)
        pivots = [0] * (self.case.n_orbitals + 1)
        phases = [0] * len(pivots)
        for index in np.argsort(-abs(state)):
            if abs(state[index]) < 1e-9:
                continue
            mask = int(self.masks[index]) | (1 << self.case.n_orbitals)
            phase = int(state[index] < 0.0)
            for orbital in reversed(range(len(pivots))):
                if not (mask >> orbital) & 1:
                    continue
                if not pivots[orbital]:
                    pivots[orbital], phases[orbital] = mask, phase
                mask ^= pivots[orbital]
                phase ^= phases[orbital]
            output[index] = (-1 if phase else 1) * abs(state[index])
        output = np.round(output, 8)
        output[output == 0.0] = 0.0
        return output.tobytes()

    def candidates(self, state, minimum=1):
        count = library.cancellations(self.dimension, len(self.gates), self.stride, self.sources, self.destinations, self.signs, self.counts, state, minimum, self.buffer)
        return self.buffer[:count].copy()

    def objective(self, labels, angles, target=None):
        gradient = np.zeros(len(angles))
        state = np.zeros(self.dimension)
        value = library.objective(self.dimension, self.stride, self.sources, self.destinations, self.signs, self.counts, self.reference, self.target if target is None else target, len(angles), np.asarray(labels, dtype=np.int32), np.asarray(angles, dtype=float), gradient, state)
        return value, gradient

    def optimize(self, labels, angles, target=None, iterations=500):
        result = minimize(lambda values: self.objective(labels, values, target), angles, jac=True, method='L-BFGS-B', options={'maxiter': iterations, 'ftol': 2e-15, 'gtol': 2e-10, 'maxls': 30})
        return result.fun, result.x

    def fit(self, labels, angles, target=None, reference=None, iterations=100):
        labels = np.asarray(labels, dtype=np.int32)
        target = self.target if target is None else target
        reference = self.reference if reference is None else reference
        output = np.zeros(self.dimension)
        jacobian = np.zeros((self.dimension, len(labels)))
        cached = None

        def calculate(parameters):
            nonlocal cached
            if cached is None or not np.array_equal(parameters, cached):
                library.circuit_jacobian(self.dimension, self.stride, self.sources, self.destinations, self.signs, self.counts, reference, len(labels), labels, parameters, output, jacobian)
                cached = parameters.copy()
            return output, jacobian

        initial, _ = calculate(np.asarray(angles, dtype=float))
        target = target * (1 if initial @ target >= 0 else -1)
        result = least_squares(lambda values: calculate(values)[0] - target, angles, jac=lambda values: calculate(values)[1], method='lm', max_nfev=iterations, ftol=1e-12, xtol=1e-12, gtol=1e-12)
        final, _ = calculate(result.x)
        return float(1.0 - (final @ target) ** 2), result.x.copy(), final.copy()

    def save(self, path, filename):
        gates = [{'annihilate': list(self.gates[label].annihilate), 'create': list(self.gates[label].create), 'theta': float((angle + math.pi) % (2 * math.pi) - math.pi)} for label, angle in reversed(path)]
        with open(filename, 'w') as handle:
            json.dump({'case_id': self.case.case_id, 'gates': gates}, handle, indent=2)

    def bridge(self, mask):
        missing = []
        for spin in range(2):
            sources = [orbital for orbital in range(spin, self.case.n_orbitals, 2) if (self.case.reference_mask >> orbital) & 1 and not (mask >> orbital) & 1]
            destinations = [orbital for orbital in range(spin, self.case.n_orbitals, 2) if (mask >> orbital) & 1 and not (self.case.reference_mask >> orbital) & 1]
            missing.extend(zip(sources, destinations))
        path = []
        for position in range(0, len(missing), 2):
            sources = tuple(sorted(entry[0] for entry in missing[position:position + 2]))
            destinations = tuple(sorted(entry[1] for entry in missing[position:position + 2]))
            if sources > destinations:
                sources, destinations = destinations, sources
            path.append((self.gates.index(Excitation(sources, destinations)), math.pi / 2))
        return list(reversed(path))

    def rebase(self, path, mask):
        forward = list(reversed(path))
        reachable = {mask: []}
        for position, (label, angle) in enumerate(forward):
            gate = self.gates[label]
            if len(gate.annihilate) != 1:
                continue
            left, right = gate.annihilate[0], gate.create[0]
            additions = {}
            for current, positions in reachable.items():
                swapped = current
                if ((current >> left) ^ (current >> right)) & 1:
                    swapped ^= (1 << left) | (1 << right)
                if swapped not in reachable:
                    additions[swapped] = positions + [position]
            reachable.update(additions)
        if self.case.reference_mask not in reachable:
            return None
        for position in reversed(reachable[self.case.reference_mask]):
            label, angle = forward[position]
            gate = self.gates[label]
            left, right = gate.annihilate[0], gate.create[0]
            forward[position] = (label, angle + math.pi / 2)
            for earlier in range(position):
                old_label, old_angle = forward[earlier]
                old_gate = self.gates[old_label]
                phase = -1 if left in old_gate.annihilate + old_gate.create else 1
                mapped = []
                for group in (old_gate.annihilate, old_gate.create):
                    transformed = [right if orbital == left else left if orbital == right else orbital for orbital in group]
                    if len(transformed) == 2 and transformed[0] > transformed[1]:
                        phase = -phase
                    mapped.append(tuple(sorted(transformed)))
                if mapped[0] > mapped[1]:
                    mapped.reverse()
                    phase = -phase
                new_label = self.gates.index(Excitation(*mapped))
                forward[earlier] = (new_label, old_angle * phase)
            if ((mask >> left) ^ (mask >> right)) & 1:
                mask ^= (1 << left) | (1 << right)
        if mask != self.case.reference_mask:
            raise RuntimeError('Reference correction failed')
        return list(reversed(forward))


def run(case_index, width, tag, symmetry=False, resume=None, parents=0, lookahead=0.0, extra=0):
    problem = Problem(load_cases()[case_index])
    beam = [(problem.target, [])]
    if resume:
        data = np.load(resume)
        beam = [(state.copy(), [(int(label), float(angle)) for label, angle in path]) for state, path in zip(data['states'], data['paths'])]
        if parents:
            beam = beam[:parents]
    started = time.time()
    for depth in range(len(beam[0][1]), problem.case.max_gates + extra):
        children = []
        metadata = []
        for parent, (state, path) in enumerate(beam):
            options = problem.candidates(state)
            for label_value, angle, support, norm in options:
                metadata.append((support, round(norm, 11), parent, int(label_value), float(angle)))
        metadata.sort()
        generated = set()
        for support, norm, parent, label, angle in metadata[:width * 30]:
            state, path = beam[parent]
            trial = apply_rotation(state, problem.pairs[label], -angle)
            distance = np.dot(trial * trial, problem.distance)
            score = (support, norm, distance)
            if lookahead:
                key = problem.canonical(trial)
                if key in generated:
                    continue
                generated.add(key)
                future = problem.candidates(trial)
                decrease = support - np.min(future[:, 2]) if len(future) else 0
                score = (support - lookahead * decrease, support, norm, distance)
            children.append((score, trial, path + [(label, float(angle))]))
        children.sort(key=lambda entry: entry[0])
        seen = set()
        beam = []
        for score, state, path in children:
            orientation = 1 if state[np.argmax(abs(state))] > 0 else -1
            key = problem.phase_key(state) if symmetry == 'phase' else problem.canonical(state) if symmetry else np.round(state * orientation, 8).tobytes()
            if key in seen:
                continue
            seen.add(key)
            beam.append((state, path))
            if np.count_nonzero(abs(state) > 1e-9) == 1:
                mask = problem.case.determinants[problem.indices[np.argmax(abs(state))]]
                bridge = problem.bridge(mask)
                rebased = problem.rebase(path, mask)
                print('DETERMINANT', depth + 1, score, 'mask', mask, 'bridge', len(bridge), flush=True)
                if rebased is not None or len(path) + len(bridge) <= problem.case.max_gates + extra:
                    problem.save(rebased if rebased is not None else path + bridge, f'{problem.case.case_id}_{tag}.json')
                    print('SOLVED', problem.case.case_id, depth + 1, time.time() - started, flush=True)
                    return
            if len(beam) >= width:
                break
        print('DEPTH', depth + 1, 'beam', len(beam), 'children', len(children), 'best', children[0][0] if children else None, 'seconds', round(time.time() - started, 2), flush=True)
        if not beam:
            break
        np.savez(f'beam_{case_index}_{tag}_{depth + 1}.npz', states=np.array([entry[0] for entry in beam]), paths=np.array([entry[1] for entry in beam]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=int)
    parser.add_argument('--width', type=int, default=500)
    parser.add_argument('--tag', default='beam')
    parser.add_argument('--symmetry', action='store_true')
    parser.add_argument('--phase-only', action='store_true')
    parser.add_argument('--resume')
    parser.add_argument('--parents', type=int, default=0)
    parser.add_argument('--lookahead', type=float, default=0.0)
    parser.add_argument('--extra', type=int, default=0)
    arguments = parser.parse_args()
    run(arguments.case, arguments.width, arguments.tag, 'phase' if arguments.phase_only else arguments.symmetry, arguments.resume, arguments.parents, arguments.lookahead, arguments.extra)

import argparse
import json
import math
from pathlib import Path

import numpy as np

from optimize import fit, gate_parameters, parameters_gates
from synthesize import load_instances, rotate, schedule


def wrap(angle):
    return float((angle + math.pi) % (2 * math.pi) - math.pi)


def simplify(instance, gates):
    gates = [dict(gate) for gate in gates]
    for gate in gates:
        if gate['u'] > gate['v']:
            gate['u'], gate['v'] = gate['v'], gate['u']
            gate['theta'] *= -1
            gate['phi'] *= -1
    changed = True
    while changed:
        changed = False
        last = {}
        for index, gate in enumerate(gates):
            first, second = gate['u'], gate['v']
            previous_index = last.get(first)
            if previous_index is not None and previous_index == last.get(second):
                previous = gates[previous_index]
                first_cosine, second_cosine = math.cos(previous['theta']), math.cos(gate['theta'])
                first_factor = math.sin(previous['theta']) * np.exp(1j * previous['phi'])
                second_factor = math.sin(gate['theta']) * np.exp(1j * gate['phi'])
                diagonal = second_cosine * first_cosine - second_factor.conjugate() * first_factor
                factor = second_factor * first_cosine + second_cosine * first_factor
                phase = float(np.angle(diagonal))
                gate['theta'] = float(np.arctan2(abs(factor), abs(diagonal)))
                gate['phi'] = wrap(float(np.angle(factor)) - phase)
                phases = {first: phase, second: -phase}
                for earlier in gates[:previous_index]:
                    earlier['phi'] = wrap(earlier['phi'] + phases.get(earlier['v'], 0) - phases.get(earlier['u'], 0))
                del gates[previous_index]
                changed = True
                break
            last[first] = last[second] = index
    initial = np.zeros(instance['n_modes'])
    initial[instance['initial_occupied']] = 1
    matrix = np.diag(initial).astype(complex)
    result = []
    for gate in gates:
        trial = rotate(matrix, gate['u'], gate['v'], gate['theta'], gate['phi'])
        if np.linalg.norm(trial - matrix) > 1e-11:
            result.append(gate)
            matrix = trial
    return result


def prune(instance, gates, output_path, trials=200):
    gates = simplify(instance, gates)
    print('SIMPLIFIED', instance['id'], len(gates), len(schedule(gates, instance['n_modes'])), flush=True)
    for iteration in range(trials):
        edges = [(gate['u'], gate['v']) for gate in gates]
        parameters = gate_parameters(gates)
        norms = np.linalg.norm(parameters.reshape(-1, 2), axis=1)
        best = None
        for index in np.argsort(norms):
            keep = np.arange(len(gates)) != index
            trial_edges = [edge for edge, retained in zip(edges, keep) if retained]
            trial_parameters = parameters.reshape(-1, 2)[keep].ravel()
            fitted, error, evaluations = fit(instance, trial_edges, trial_parameters, max_evaluations=100)
            if best is None or error < best[0]:
                best = (error, int(index), fitted, trial_edges)
            if error < 1e-9:
                break
        error, index, fitted, trial_edges = best
        print('PRUNE', instance['id'], 'gates', len(gates), 'remove', index, 'error', error, flush=True)
        if error > 1e-9:
            break
        gates = simplify(instance, parameters_gates(trial_edges, fitted))
        circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
        Path(output_path).write_text(json.dumps(circuit))
    circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
    Path(output_path).write_text(json.dumps(circuit))
    return circuit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('circuit')
    parser.add_argument('--output')
    arguments = parser.parse_args()
    circuit = json.loads(Path(arguments.circuit).read_text())
    instance = next(instance for instance in load_instances() if instance['id'] == circuit['id'])
    gates = [gate for layer in circuit['layers'] for gate in layer]
    prune(instance, gates, arguments.output or circuit['id'] + '_compressed.json')


if __name__ == '__main__':
    main()

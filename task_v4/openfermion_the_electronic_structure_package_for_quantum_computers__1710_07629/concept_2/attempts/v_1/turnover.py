import argparse
import time
from optimize import *


def canonical(gates, size):
    layers = schedule(gates, size)
    return tuple(tuple(sorted(tuple(sorted((gate['u'], gate['v']))) for gate in layer)) for layer in layers)


def push_phases(gates, stop, phases):
    result = list(gates)
    for index in range(stop):
        first, second, theta, phi = result[index]
        phi = np.angle(np.exp(1j * (phi + phases.get(second, 0) - phases.get(first, 0))))
        result[index] = first, second, theta, float(phi)
    return result


def factor_block(gates, indices, path, pattern):
    unitary = np.eye(len(path), dtype=complex)
    for index in indices:
        first, second, theta, phi = gates[index]
        local = [path.index(first), path.index(second)]
        block = gate_data([theta * np.cos(phi), theta * np.sin(phi)])[0]
        unitary[local] = block @ unitary[local]
    elimination = []
    for first, second, column in pattern:
        upper, lower = unitary[first, column], unitary[second, column]
        theta = math.atan2(abs(lower), abs(upper))
        phi = float(np.angle(-lower / upper)) if abs(upper) > 1e-14 else 0.0
        block = gate_data([theta * np.cos(phi), theta * np.sin(phi)])[0]
        unitary[[first, second]] = block @ unitary[[first, second]]
        elimination.append((path[first], path[second], -theta, phi))
    phases = {mode: float(np.angle(unitary[index, index])) for index, mode in enumerate(path)}
    result = push_phases(gates, indices[0], phases)
    replacement = list(reversed(elimination))
    selected = set(indices)
    output = []
    for index, gate in enumerate(result):
        if index == indices[0]:
            output.extend(replacement)
        if index not in selected:
            output.append(gate)
    return output


def simplify(gates, instance):
    changed = True
    while changed:
        changed = False
        matrix = np.diag([complex(mode in instance['initial_occupied']) for mode in range(instance['n_modes'])])
        kept = []
        for gate in gates:
            after = rotate(matrix, *gate)
            if np.linalg.norm(after - matrix) < 1e-11:
                changed = True
            else:
                kept.append(gate)
                matrix = after
        gates = kept
        for first_index, gate in enumerate(gates):
            support = set(gate[:2])
            for second_index in range(first_index + 1, len(gates)):
                following = set(gates[second_index][:2])
                if support & following:
                    if support == following:
                        path = list(gate[:2])
                        gates = factor_block(gates, [first_index, second_index], path, [(0, 1, 0)])
                        changed = True
                    break
            if changed:
                break
    return gates


def moves(gates):
    for first_index, first_gate in enumerate(gates):
        first_support = set(first_gate[:2])
        for second_index in range(first_index + 1, len(gates)):
            second_support = set(gates[second_index][:2])
            if not first_support & second_support:
                continue
            if first_support == second_support:
                break
            support = first_support | second_support
            if any(set(gate[:2]) & support for gate in gates[first_index + 1:second_index]):
                break
            for third_index in range(second_index + 1, len(gates)):
                third_support = set(gates[third_index][:2])
                if not support & third_support:
                    continue
                if third_support == first_support:
                    center = next(iter(first_support & second_support))
                    left = next(iter(first_support - {center}))
                    right = next(iter(second_support - {center}))
                    yield factor_block(gates, [first_index, second_index, third_index], [left, center, right], [(1, 2, 0), (0, 1, 0), (1, 2, 1)])
                break
            break


def search(instance, source='local', width=100, iterations=200):
    circuit = json.loads(Path(instance['id'] + '_' + source + '.json').read_text())
    original = [(gate['u'], gate['v'], gate['theta'], gate['phi']) for layer in circuit['layers'] for gate in layer]
    original = simplify(original, instance)
    beam = [original]
    visited = {canonical(original, instance['n_modes'])}
    best = (len(original), len(schedule(original, instance['n_modes'])))
    started = time.monotonic()
    for iteration in range(iterations):
        following = []
        for gates in beam:
            for result in moves(gates):
                result = simplify(result, instance)
                signature = canonical(result, instance['n_modes'])
                if signature in visited:
                    continue
                visited.add(signature)
                depth = len(signature)
                score = len(result), depth
                if score < best:
                    best = score
                    circuit = dict(id=instance['id'], layers=schedule(result, instance['n_modes']))
                    Path(instance['id'] + '_turnover.json').write_text(json.dumps(circuit))
                    print('BEST', instance['id'], iteration, score, flush=True)
                    if score[0] <= instance['budgets']['max_gates'] and score[1] <= instance['budgets']['max_depth']:
                        print('SOLVED', instance['id'], flush=True)
                        return
                angle_score = sum(min(abs(gate[2]), abs(abs(gate[2]) - np.pi / 2)) for gate in result)
                following.append((score, angle_score, result))
        following.sort(key=lambda item: (item[0], item[1]))
        beam = [result for _, _, result in following[:width]]
        print(instance['id'], iteration, len(following), len(visited), 'best', best, 'time', round(time.monotonic() - started, 1), flush=True)
        if not beam:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--source', default='local')
    parser.add_argument('--width', type=int, default=100)
    arguments = parser.parse_args()
    search(INSTANCES[arguments.index], arguments.source, arguments.width)

import argparse
import time
from optimize import *


def insertion_candidates(instance, edges, parameters):
    solver = Fit(instance, edges)
    frames = [solver.initial.copy()]
    matrices = []
    for edge, pair in zip(edges, parameters):
        matrix = gate_data(pair)[0]
        matrices.append(matrix)
        frame = frames[-1].copy()
        frame[list(edge)] = matrix @ frame[list(edge)]
        frames.append(frame)
    backward = solver.empty.conj().T @ (solver.empty @ frames[-1])
    proposals = []
    for position in range(len(edges), -1, -1):
        frame = frames[position]
        for first, second in instance['edges']:
            if position and first not in edges[position - 1] and second not in edges[position - 1]:
                continue
            cross_first = np.vdot(backward[first], frame[second])
            cross_second = np.vdot(backward[second], frame[first])
            horizontal = (-cross_first + cross_second).real
            vertical = (1j * cross_first + 1j * cross_second).real
            proposals.append((horizontal ** 2 + vertical ** 2, position, (first, second)))
        if position:
            edge = list(edges[position - 1])
            backward[edge] = matrices[position - 1].conj().T @ backward[edge]
    proposals.sort(reverse=True)
    return proposals


def search(instance, width=1, choices=8):
    beam = [(np.linalg.norm(target(instance) - np.diag([int(mode in instance['initial_occupied']) for mode in range(instance['n_modes'])])), [], np.zeros((0, 2)))]
    started = time.monotonic()
    for count in range(1, instance['budgets']['max_gates'] + 1):
        following = []
        for previous_error, edges, parameters in beam:
            proposals = insertion_candidates(instance, edges, parameters)
            attempts = 0
            for gain, position, edge in proposals:
                trial_edges = edges[:position] + [edge] + edges[position:]
                depth = len(schedule([(first, second, 0, 0) for first, second in trial_edges], instance['n_modes']))
                if depth > instance['budgets']['max_depth']:
                    continue
                trial_parameters = np.insert(parameters, position, [0.0, 0.0], axis=0)
                solver = Fit(instance, trial_edges)
                trial_parameters, error = solver.solve(trial_parameters, evaluations=100, tolerance=1e-10)
                following.append((error, trial_edges, trial_parameters))
                attempts += 1
                if error < 1e-9:
                    circuit = pack(instance, trial_edges, trial_parameters)
                    Path(instance['id'] + '_adapt.json').write_text(json.dumps(circuit))
                    print('SOLVED', instance['id'], count, len(circuit['layers']), error, flush=True)
                    return
                if attempts >= choices:
                    break
        if not following:
            break
        following.sort(key=lambda item: item[0])
        beam = following[:width]
        error, edges, parameters = beam[0]
        Path(instance['id'] + '_adapt_partial.json').write_text(json.dumps(pack(instance, edges, parameters)))
        print(instance['id'], count, error, 'time', round(time.monotonic() - started, 2), flush=True)
    print('FAILED', instance['id'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--width', type=int, default=1)
    parser.add_argument('--choices', type=int, default=8)
    arguments = parser.parse_args()
    search(INSTANCES[arguments.index], arguments.width, arguments.choices)

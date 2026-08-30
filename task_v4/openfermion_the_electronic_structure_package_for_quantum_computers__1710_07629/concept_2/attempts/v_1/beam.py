import argparse
import time
from minor_peel import *
from local_compile import LocalCompiler


def search(instance, width=40, order=1, grams=False):
    matrix = target(instance)
    initial = np.array([int(mode in instance['initial_occupied']) for mode in range(len(matrix))])
    distances = np.full(matrix.shape, 100.0)
    np.fill_diagonal(distances, 0)
    for first, second in instance['edges']:
        distances[first, second] = distances[second, first] = 1
    for center in range(len(matrix)):
        distances = np.minimum(distances, distances[:, center, None] + distances[None, center, :])
    beam = [(matrix, [], 0.0)]
    local = LocalCompiler(instance)
    started = time.monotonic()
    for step in range(instance['budgets']['max_gates']):
        following = {}
        for matrix, previous, rewards in beam:
            modes = minimal_modes(matrix, 3)
            choices = list(minor_candidates(matrix, instance['edges'], modes, order))
            if grams:
                choices.extend(gram_candidates(matrix, instance['edges'], modes))
            for first, second in instance['edges']:
                outside = [mode for mode in range(len(matrix)) if mode not in (first, second)]
                if np.linalg.norm(matrix[np.ix_([first, second], outside)]) < 1e-10:
                    for gate in candidates(matrix, [(first, second)]):
                        choices.append((100, 100, gate))
            per_edge = {}
            for weight, contexts, gate in choices:
                per_edge.setdefault(gate[:2], []).append((weight, contexts, gate))
            choices = []
            for edge_choices in per_edge.values():
                edge_choices.sort(reverse=True)
                choices.extend(edge_choices[:12])
                if grams:
                    choices.extend([entry for entry in edge_choices[12:] if entry[0] == 1.0 and entry[1] == 1])
            maximum_weight = max((weight for weight, _, _ in choices), default=1)
            for weight, contexts, gate in choices:
                result = rotate(matrix, *gate)
                diagonal = result.diagonal().real
                if np.any(abs(diagonal - (1 - initial)) < 1e-9):
                    continue
                active = tuple(np.flatnonzero(abs(diagonal - initial) > 1e-9))
                if not local.split_valid(result, active):
                    continue
                gates = previous + [gate]
                depth = len(schedule(gates, len(matrix)))
                if depth > instance['budgets']['max_depth']:
                    continue
                error = np.linalg.norm(result - np.diag(initial))
                if error < 1e-8:
                    inverse = [(first, second, -theta, phi) for first, second, theta, phi in reversed(gates)]
                    circuit = dict(id=instance['id'], layers=schedule(inverse, len(matrix)))
                    Path(instance['id'] + '_beam.json').write_text(json.dumps(circuit))
                    print('SOLVED', instance['id'], len(gates), len(circuit['layers']), error, flush=True)
                    return circuit
                zeros = np.count_nonzero(abs(result) < 1e-9)
                locality = np.sum(abs(result) ** 2 * distances ** 2)
                impurity = np.sum(diagonal * (1 - diagonal))
                pure = np.count_nonzero(abs(diagonal - initial) < 1e-9)
                reward = rewards + math.log(max(weight / maximum_weight, 1e-12))
                score = (-zeros, -pure, round(locality, 8), round(impurity, 8), depth, -reward)
                real = np.round(result.real, 8)
                imag = np.round(result.imag, 8)
                real[real == 0] = 0
                imag[imag == 0] = 0
                signature = real.tobytes() + imag.tobytes()
                if signature not in following or score < following[signature][0]:
                    following[signature] = (score, result, gates, reward)
        selected = []
        used = set()
        rankings = [lambda item: item[1][0],
                    lambda item: (item[1][0][5], item[1][0][0]),
                    lambda item: (item[1][0][2], item[1][0][0]),
                    lambda item: (item[1][0][1], item[1][0][4], item[1][0][2])]
        for ranking in rankings:
            added = 0
            for signature, entry in sorted(following.items(), key=ranking):
                if signature in used:
                    continue
                used.add(signature)
                selected.append(entry)
                added += 1
                if added >= max(1, width // len(rankings)):
                    break
        beam = [(result, gates, rewards) for score, result, gates, rewards in selected]
        print(instance['id'], step + 1, len(following), 'best', selected[0][0] if selected else None,
              'time', round(time.monotonic() - started, 2), flush=True)
        if not beam:
            break
    print('FAILED', instance['id'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--width', type=int, default=40)
    parser.add_argument('--order', type=int, default=1)
    parser.add_argument('--grams', action='store_true')
    arguments = parser.parse_args()
    search(INSTANCES[arguments.index], arguments.width, arguments.order, arguments.grams)

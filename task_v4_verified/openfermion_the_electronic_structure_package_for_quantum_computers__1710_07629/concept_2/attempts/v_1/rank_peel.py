import argparse
import itertools
from functools import lru_cache
from peel import *


@lru_cache(None)
def groups(size, count):
    return np.array(list(itertools.combinations(range(size), count)), dtype=int)


def minimal_modes(matrix, max_size=6):
    modes = []
    for count in range(1, min(max_size, len(matrix)) + 1):
        subsets = groups(len(matrix), count)
        values, vectors = np.linalg.eigh(matrix[subsets[:, :, None], subsets[:, None, :]])
        for occupation in (0, 1):
            near = abs(values - occupation) < 2e-12
            selected = np.flatnonzero(np.sum(near, axis=1) == 1)
            for index in selected:
                vector = vectors[index, :, np.flatnonzero(near[index])[0]]
                if np.min(abs(vector)) < 1e-7:
                    continue
                modes.append((tuple(subsets[index]), occupation, vector))
    return modes


def mode_candidates(matrix, edges, modes):
    for first, second in edges:
        allowed = True
        for column in range(len(matrix)):
            if column in (first, second):
                continue
            if (abs(matrix[first, column]) < 1e-11) != (abs(matrix[second, column]) < 1e-11):
                allowed = False
                break
        if not allowed:
            continue
        for subset, occupation, vector in modes:
            if (first in subset) == (second in subset):
                continue
            outside = second if first in subset else first
            enlarged = subset + (outside,)
            values = np.linalg.eigvalsh(matrix[np.ix_(enlarged, enlarged)])
            if np.count_nonzero(abs(values - occupation) < 2e-12) < 2:
                allowed = False
                break
        if not allowed:
            continue
        clusters = {}
        for subset, occupation, vector in modes:
            if first not in subset or second not in subset:
                continue
            ratio = -vector[subset.index(second)] / vector[subset.index(first)]
            if abs(ratio) > 1:
                ratio = -1 / ratio.conjugate()
            key = round(ratio.real, 7), round(ratio.imag, 7)
            if key not in clusters:
                clusters[key] = [ratio, 0.0, 0, len(subset)]
            clusters[key][1] += 2.0 ** (-len(subset))
            clusters[key][2] += 1
        for ratio, weight, count, support_size in clusters.values():
            theta, phi = math.atan(abs(ratio)), float(np.angle(ratio))
            if theta < 1e-9:
                continue
            yield weight, count, support_size, (first, second, theta, phi)
            yield weight, count, support_size, (first, second, theta - math.pi / 2, phi)
        previous = np.count_nonzero(abs(matrix) < 1e-10)
        for gate in candidates(matrix, [(first, second)]):
            result = rotate(matrix, *gate)
            gain = np.count_nonzero(abs(result) < 1e-10) - previous
            if gain >= 4:
                yield 0.0, 0, 0, gate


def run(instance, max_size=6):
    matrix = target(instance)
    distances = np.full(matrix.shape, 100.0)
    np.fill_diagonal(distances, 0)
    for first, second in instance['edges']:
        distances[first, second] = distances[second, first] = 1
    for center in range(len(matrix)):
        distances = np.minimum(distances, distances[:, center, None] + distances[None, center, :])
    initial = np.array([int(mode in instance['initial_occupied']) for mode in range(len(matrix))])
    gates = []
    for step in range(instance['budgets']['max_gates'] + 10):
        modes = minimal_modes(matrix, max_size)
        choices = []
        for weight, count, support_size, gate in mode_candidates(matrix, instance['edges'], modes):
            result = rotate(matrix, *gate)
            diagonal = result.diagonal().real
            wrong = np.any((abs(diagonal - (1 - initial)) < 1e-10))
            if wrong:
                continue
            impurity = np.sum(diagonal * (1 - diagonal))
            distance = np.linalg.norm(result - np.diag(initial))
            zeros = np.count_nonzero(abs(result) < 1e-10) - np.count_nonzero(abs(matrix) < 1e-10)
            locality = np.sum(abs(result) ** 2 * distances ** 2)
            choices.append(((zeros, weight, count, -round(locality, 9), -round(impurity, 9), -round(distance, 9), -abs(gate[2])), gate, result))
        if not choices:
            print('STUCK', step, len(modes), flush=True)
            break
        score, gate, matrix = max(choices, key=lambda item: item[0])
        gates.append(gate)
        error = np.linalg.norm(matrix - np.diag(initial))
        print(instance['id'], step, len(modes), len(choices), gate, score, 'err', error, flush=True)
        if error < 1e-8:
            break
    inverse = [(first, second, -theta, phi) for first, second, theta, phi in reversed(gates)]
    circuit = dict(id=instance['id'], layers=schedule(inverse, len(matrix)))
    Path(instance['id'] + '_rank.json').write_text(json.dumps(circuit))
    print('FINAL', instance['id'], len(gates), len(circuit['layers']), np.linalg.norm(matrix - np.diag(initial)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--max-size', type=int, default=6)
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.max_size)

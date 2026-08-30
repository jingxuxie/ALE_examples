import argparse
import itertools
from rank_peel import minimal_modes
from rank_peel import groups
from peel import *


def admissible(matrix, edges, modes):
    for first, second in edges:
        outside = [mode for mode in range(len(matrix)) if mode not in (first, second)]
        if np.any((abs(matrix[first, outside]) < 1e-10) != (abs(matrix[second, outside]) < 1e-10)):
            continue
        allowed = True
        for subset, occupation, vector in modes:
            if (first in subset) == (second in subset):
                continue
            neighbor = second if first in subset else first
            enlarged = subset + (neighbor,)
            values = np.linalg.eigvalsh(matrix[np.ix_(enlarged, enlarged)])
            if np.count_nonzero(abs(values - occupation) < 2e-12) < 2:
                allowed = False
                break
        if allowed:
            yield first, second


def cluster_ratios(upper, lower, clusters, order, minimum=2):
    valid = (abs(upper) > 1e-11) & (abs(lower) > 1e-11)
    if not np.any(valid):
        return
    upper, lower = upper[valid], lower[valid]
    ratios = -lower / upper
    swapped = abs(ratios) > 1
    ratios[swapped] = -1 / ratios[swapped].conj()
    keys = np.round(np.column_stack((ratios.real, ratios.imag)), 7)
    unique, first_indices, inverse, counts = np.unique(keys, axis=0, return_index=True, return_inverse=True, return_counts=True)
    for index in np.flatnonzero(counts >= minimum):
        key = tuple(unique[index])
        mask = inverse == index
        quality = np.maximum(abs(upper[mask]), abs(lower[mask]))
        ratio = ratios[mask][np.argmax(quality)]
        weight = counts[index] / (10 ** order)
        if key not in clusters:
            clusters[key] = [ratio, 0.0, 0, 0.0]
        clusters[key][1] += weight
        clusters[key][2] += 1
        if quality.max() > clusters[key][3]:
            clusters[key][0] = ratio
            clusters[key][3] = quality.max()


def minor_candidates(matrix, edges, modes, order=1):
    for first, second in admissible(matrix, edges, modes):
        outside = [mode for mode in range(len(matrix)) if mode not in (first, second)]
        clusters = {}
        cluster_ratios(matrix[first, outside], matrix[second, outside], clusters, 0)
        columns = np.array(list(itertools.combinations(outside, 2)), dtype=int)
        for auxiliary in outside:
            upper = matrix[auxiliary, columns[:, 0]] * matrix[first, columns[:, 1]] - matrix[auxiliary, columns[:, 1]] * matrix[first, columns[:, 0]]
            lower = matrix[auxiliary, columns[:, 0]] * matrix[second, columns[:, 1]] - matrix[auxiliary, columns[:, 1]] * matrix[second, columns[:, 0]]
            cluster_ratios(upper, lower, clusters, 1)
        if order >= 2:
            columns = np.array(list(itertools.combinations(outside, 3)), dtype=int)
            for auxiliary_first, auxiliary_second in itertools.combinations(outside, 2):
                row_first = matrix[auxiliary_first, columns]
                row_second = matrix[auxiliary_second, columns]
                cross = np.cross(row_first, row_second)
                upper = np.sum(cross * matrix[first, columns], axis=1)
                lower = np.sum(cross * matrix[second, columns], axis=1)
                cluster_ratios(upper, lower, clusters, 2, minimum=3)
        for ratio, weight, contexts, quality in clusters.values():
            theta, phi = math.atan(abs(ratio)), float(np.angle(ratio))
            if theta < 1e-8:
                continue
            yield weight, contexts, (first, second, theta, phi)
            yield weight, contexts, (first, second, theta - math.pi / 2, phi)


def gram_candidates(matrix, edges, modes, max_size=4):
    for first, second in admissible(matrix, edges, modes):
        outside = np.array([mode for mode in range(len(matrix)) if mode not in (first, second)])
        clusters = {}
        for size in range(2, min(max_size, len(outside)) + 1):
            subsets = outside[groups(len(outside), size)]
            upper = matrix[first, subsets]
            lower = matrix[second, subsets]
            diagonal_first = np.sum(abs(upper) ** 2, axis=1)
            diagonal_second = np.sum(abs(lower) ** 2, axis=1)
            cross = np.sum(upper * lower.conj(), axis=1)
            determinant = diagonal_first * diagonal_second - abs(cross) ** 2
            valid = (determinant > 1e-12) & (abs(cross) > 1e-12)
            angles = 0.5 * np.arctan2(2 * abs(cross[valid]), diagonal_second[valid] - diagonal_first[valid])
            phases = -np.angle(cross[valid])
            angles[angles > np.pi / 4] -= np.pi / 2
            ratios = np.tan(angles) * np.exp(1j * phases)
            cluster_ratios(np.ones(len(ratios)), -ratios, clusters, size - 2, minimum=2)
        for ratio, weight, contexts, quality in clusters.values():
            theta, phi = math.atan(abs(ratio)), float(np.angle(ratio))
            if theta < 1e-8:
                continue
            yield weight, contexts, (first, second, theta, phi)
            yield weight, contexts, (first, second, theta - math.pi / 2, phi)
        upper, lower = matrix[first, first].real, matrix[second, second].real
        cross = matrix[first, second]
        if abs(cross) > 1e-12:
            theta = 0.5 * math.atan2(2 * abs(cross), lower - upper)
            phi = -float(np.angle(cross))
            yield 1.0, 1, (first, second, theta, phi)
            yield 1.0, 1, (first, second, theta - math.pi / 2, phi)


def run(instance, order=1, variant=0):
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
        modes = minimal_modes(matrix, 5)
        choices = []
        for weight, contexts, gate in minor_candidates(matrix, instance['edges'], modes, order):
            result = rotate(matrix, *gate)
            diagonal = result.diagonal().real
            if np.any(abs(diagonal - (1 - initial)) < 1e-10):
                continue
            zeros = np.count_nonzero(abs(result) < 1e-10) - np.count_nonzero(abs(matrix) < 1e-10)
            locality = np.sum(abs(result) ** 2 * distances ** 2)
            sparse_locality = np.sum((abs(result) > 1e-10) * distances ** 2)
            impurity = np.sum(diagonal * (1 - diagonal))
            if variant == 0:
                score = (round(weight, 5), zeros, -round(locality, 9), -round(impurity, 9))
            elif variant == 1:
                score = (zeros, round(weight, 5), -sparse_locality, -round(locality, 9))
            elif variant == 2:
                score = (round(weight, 5), zeros, -sparse_locality, -round(locality, 9))
            else:
                score = (-round(locality, 9), round(weight, 5), zeros)
            choices.append((score, gate, result))
        if not choices:
            print('STUCK', step, len(modes), flush=True)
            break
        score, gate, matrix = max(choices, key=lambda item: item[0])
        gates.append(gate)
        error = np.linalg.norm(matrix - np.diag(initial))
        print(instance['id'], step, len(choices), gate, score, 'err', error, flush=True)
        if error < 1e-8:
            break
    inverse = [(first, second, -theta, phi) for first, second, theta, phi in reversed(gates)]
    circuit = dict(id=instance['id'], layers=schedule(inverse, len(matrix)))
    Path(instance['id'] + f'_minor{order}_{variant}.json').write_text(json.dumps(circuit))
    print('FINAL', instance['id'], len(gates), len(circuit['layers']), np.linalg.norm(matrix - np.diag(initial)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--order', type=int, default=1)
    parser.add_argument('--variant', type=int, default=0)
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.order, arguments.variant)

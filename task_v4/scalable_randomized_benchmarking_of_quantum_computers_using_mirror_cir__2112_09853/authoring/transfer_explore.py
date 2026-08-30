import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar


def conjugate(labels, gates, width):
    labels = np.array(labels, dtype=np.int64, copy=True)
    bitmask = (1 << width) - 1
    xbits = labels & bitmask
    zbits = labels >> width
    for gate in gates:
        kind, first = gate[:2]
        if kind == 'H':
            change = ((xbits >> first) ^ (zbits >> first)) & 1
            xbits ^= change << first
            zbits ^= change << first
        elif kind == 'S':
            zbits ^= ((xbits >> first) & 1) << first
        elif kind == 'CX':
            second = gate[2]
            xbits ^= ((xbits >> first) & 1) << second
            zbits ^= ((zbits >> second) & 1) << first
        else:
            raise ValueError(kind)
    return xbits | (zbits << width)


def make_model(seed=191, width=4):
    random = np.random.default_rng(seed)
    local_words = [[], ['H'], ['S'], ['H', 'S'], ['S', 'H'], ['H', 'S', 'H']]
    layers = []
    edges = [(site, (site + 1) % width) for site in range(width)]
    for index in range(48):
        gates = []
        if index % 4:
            first, second = edges[index % width]
            if index % 2:
                first, second = second, first
            gates.append(['CX', first, second])
            idle = [site for site in range(width) if site not in (first, second)]
        else:
            idle = list(range(width))
        for site in idle:
            gates.extend([[kind, site] for kind in local_words[int(random.integers(6))]])
        layers.extend([gates, list(reversed(gates))])
    labels = np.arange(1, 4 ** width, dtype=np.int64)
    permutations = np.array([conjugate(labels, gates, width) - 1 for gates in layers])
    support = [int(label) for label in labels
               if bin((int(label) & ((1 << width) - 1)) | (int(label) >> width)).count('1') <= 2]
    source = np.array(support)
    xbits = source & ((1 << width) - 1)
    zbits = source >> width
    target_x = labels & ((1 << width) - 1)
    target_z = labels >> width
    parity = (xbits[:, None] & target_z) ^ (zbits[:, None] & target_x)
    signs = np.array([1 - 2 * (bin(int(value)).count('1') % 2) for value in parity.flat]).reshape(parity.shape)
    inverse = np.arange(len(layers)) ^ 1
    return layers, support, permutations, signs, inverse


def transfer(probabilities, rate, permutations, signs, inverse):
    eigenvalues = 1 + rate * np.asarray(probabilities) @ (signs - 1)
    rows = np.broadcast_to(np.arange(permutations.shape[1]), permutations.shape)
    weights = eigenvalues[inverse] * np.take_along_axis(eigenvalues, permutations, axis=1)
    matrix = np.zeros((permutations.shape[1], permutations.shape[1]))
    np.add.at(matrix, (rows.ravel(), permutations.ravel()), weights.ravel() / len(permutations))
    return matrix


def score(matrix, rate, depths=None):
    if depths is None:
        depths = np.array([0, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128])
    vector = np.ones(matrix.shape[0])
    values = {0: 1.0}
    for halfdepth in range(1, int(max(depths)) // 2 + 1):
        vector = matrix @ vector
        values[2 * halfdepth] = float(vector.mean())
    signal = np.array([values[int(depth)] for depth in depths])
    def objective(decay):
        shape = np.exp(-decay * depths)
        amplitude = np.clip(np.dot(shape, signal) / np.dot(shape, shape), 0, 1.1)
        return float(np.mean((amplitude * shape - signal) ** 2))
    fitted = minimize_scalar(objective, bounds=(0, rate * 3), method='bounded', options={'xatol': 1e-13})
    inferred = (matrix.shape[0] / (matrix.shape[0] + 1)) * (-np.expm1(-fitted.x))
    return {'bias': float(1 - inferred / rate), 'rate': float(inferred),
            'rmse': float(np.sqrt(fitted.fun)), 'signal': signal.tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=200)
    parser.add_argument('--rate', type=float, default=0.03)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    layers, support, permutations, signs, inverse = make_model()
    ideal = transfer(np.ones((len(layers), len(support))) / len(support), 0, permutations, signs, inverse)
    spectrum = np.linalg.eigvalsh(ideal)
    random = np.random.default_rng(753289)
    best = None
    for index in range(arguments.samples):
        probabilities = np.zeros((len(layers), len(support)))
        if index < len(support):
            probabilities[:, index] = 1
        else:
            probabilities[np.arange(len(layers)), random.integers(len(support), size=len(layers))] = 1
        result = score(transfer(probabilities, arguments.rate, permutations, signs, inverse), arguments.rate)
        if best is None or result['bias'] > best['metrics']['bias']:
            best = {'metrics': result, 'probabilities': probabilities.tolist(), 'index': index}
            print(index, result['bias'], result['rmse'], flush=True)
    arguments.output.write_text(json.dumps({'best': best, 'ideal_gap': float(1-spectrum[-2]),
                                           'support': support, 'layers': layers}, indent=2) + '\n')


if __name__ == '__main__':
    main()

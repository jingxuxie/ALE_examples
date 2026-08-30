import argparse
import numpy as np


def compress(catalogue):
    source = catalogue['source']
    target = catalogue['target']
    channels = catalogue['channels']
    state_count = len(catalogue['velocities'])
    edge_count = len(source)
    importance = np.zeros(edge_count)
    for coefficients in catalogue['mixing']:
        weights = channels @ coefficients
        degree = np.bincount(source, weights=weights, minlength=state_count)
        degree += np.bincount(target, weights=weights, minlength=state_count)
        importance += weights * (1 / degree[source] + 1 / degree[target])
    probabilities = importance / importance.sum()
    generator = np.random.default_rng(29)
    sample = generator.choice(edge_count, int(catalogue['budget']), p=probabilities)
    indices, counts = np.unique(sample, return_counts=True)
    multipliers = counts / (int(catalogue['budget']) * probabilities[indices])
    return indices, multipliers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as data:
        indices, multipliers = compress(data)
    np.savez(args.output, indices=indices, multipliers=multipliers)


if __name__ == '__main__':
    main()

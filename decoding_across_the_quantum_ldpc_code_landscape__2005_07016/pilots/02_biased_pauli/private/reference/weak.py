import argparse
import numpy as np


def decode(case):
    checks = np.concatenate((case['gz'], case['gx']), axis=1).copy()
    target = case['syndrome'].T.copy()
    probabilities = case['pauli_probs']
    marginal = np.concatenate((probabilities[:, 1] + probabilities[:, 2],
                               probabilities[:, 3] + probabilities[:, 2]))
    column_order = np.argsort(-marginal, kind='stable')
    checks = checks[:, column_order]
    pivots = []
    pivot_row = 0
    for column in range(checks.shape[1]):
        candidates = np.flatnonzero(checks[pivot_row:, column])
        if not candidates.size:
            continue
        selected = pivot_row + candidates[0]
        checks[[pivot_row, selected]] = checks[[selected, pivot_row]]
        target[[pivot_row, selected]] = target[[selected, pivot_row]]
        affected = np.flatnonzero(checks[:, column])
        affected = affected[affected != pivot_row]
        checks[affected] ^= checks[pivot_row]
        target[affected] ^= target[pivot_row]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == checks.shape[0]:
            break
    if np.any(target[pivot_row:]):
        raise ValueError('Inconsistent syndrome')
    ordered = np.zeros((checks.shape[1], target.shape[1]), dtype=np.uint8)
    ordered[pivots] = target[:pivot_row]
    correction = np.zeros_like(ordered)
    correction[column_order] = ordered
    block_length = probabilities.shape[0]
    return correction[:block_length].T, correction[block_length:].T


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        correction_x, correction_z = decode(archive)
    np.savez_compressed(args.output, correction_x=correction_x,
                        correction_z=correction_z)


if __name__ == '__main__':
    main()

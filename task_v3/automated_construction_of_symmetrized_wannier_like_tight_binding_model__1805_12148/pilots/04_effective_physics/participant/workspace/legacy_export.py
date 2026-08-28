import argparse
import numpy as np


def export(case):
    selected = case['target']
    dimension = len(selected)
    result = {
        'U': np.eye(dimension, dtype=complex),
        'H0': np.diag(case['energy'][selected]).astype(complex),
        'H1': np.stack([matrix[np.ix_(selected, selected)] for matrix in case['momentum']], axis=-1) * (2 * 3.809982208629016 / 0.52917721067),
        'H2': np.einsum('ij,ab->ijab', np.eye(dimension), np.eye(3)).astype(complex) * 3.809982208629016,
        'H3': np.zeros((dimension, dimension, 3, 3, 3), dtype=complex),
        'G': np.moveaxis(case['spin'], 0, -1).astype(complex),
    }
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = export(dict(archive))
    np.savez_compressed(arguments.output, **result)

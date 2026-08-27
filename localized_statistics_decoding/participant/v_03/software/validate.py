import argparse
import json

import numpy as np


def compare(data, labels, predictions):
    correction = predictions['correction']
    expected_shape = (len(data['syndrome']), data['H'].shape[1])
    if correction.shape != expected_shape or not np.isin(correction, [0, 1]).all():
        raise ValueError('correction must be binary with shape ' + str(expected_shape))
    correction = correction.astype(np.uint8)
    valid = ((correction @ data['H'].T) % 2 == data['syndrome']).all(axis=1)
    recovered = valid & (((correction @ data['L'].T) % 2) == labels['logical_target']).all(axis=1)
    weights = np.log((1 - data['prior']) / data['prior'])
    valid_fraction = float(valid.mean())
    recovery_fraction = float(recovered.mean())
    return {'frames': len(valid), 'syndrome_fraction': valid_fraction,
            'logical_recovery_fraction': recovery_fraction,
            'score': 0.15 * valid_fraction + 0.85 * min(1.0, recovery_fraction / 0.85),
            'mean_candidate_cost': float(np.mean(correction @ weights)),
            'mean_candidate_weight': float(correction.sum(axis=1).mean())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--labels', required=True)
    parser.add_argument('--actual', required=True)
    arguments = parser.parse_args()
    print(json.dumps(compare(np.load(arguments.input, allow_pickle=False),
                             np.load(arguments.labels, allow_pickle=False),
                             np.load(arguments.actual, allow_pickle=False))))

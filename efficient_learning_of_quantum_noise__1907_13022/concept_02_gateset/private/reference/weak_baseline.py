import sys

import numpy as np
from scipy.optimize import nnls


def ideal_signs(data, prefix):
    signs = []
    for begin, end, observable in zip(data[prefix + '_ptr'][:-1], data[prefix + '_ptr'][1:],
                                      data[prefix + '_observable']):
        pauli_x = ((observable == 1) | (observable == 2)).astype(np.int8)
        pauli_z = ((observable == 2) | (observable == 3)).astype(np.int8)
        phase = 0
        for gate in data[prefix + '_gates'][begin:end][::-1]:
            operations = data['gate_ops'][data['gate_ptr'][gate]:data['gate_ptr'][gate + 1]]
            for opcode, first, second in operations[::-1]:
                if opcode == 1:
                    phase ^= int(pauli_x[first] & pauli_z[first])
                    pauli_x[first], pauli_z[first] = pauli_z[first], pauli_x[first]
                elif opcode == 2:
                    phase ^= int(pauli_x[first] & (1 ^ pauli_z[first]))
                    pauli_z[first] ^= pauli_x[first]
                elif opcode in (3, 4):
                    if opcode == 4:
                        phase ^= int(pauli_x[second] & pauli_z[second])
                        pauli_x[second], pauli_z[second] = pauli_z[second], pauli_x[second]
                    phase ^= int(pauli_x[first] & pauli_z[second] &
                                 (pauli_x[second] ^ pauli_z[first] ^ 1))
                    pauli_x[second] ^= pauli_x[first]
                    pauli_z[first] ^= pauli_z[second]
                    if opcode == 4:
                        phase ^= int(pauli_x[second] & pauli_z[second])
                        pauli_x[second], pauli_z[second] = pauli_z[second], pauli_x[second]
                elif opcode == 5:
                    pauli_x[first], pauli_x[second] = pauli_x[second], pauli_x[first]
                    pauli_z[first], pauli_z[second] = pauli_z[second], pauli_z[first]
        signs.append(1 - 2 * phase)
    return np.array(signs)


def solve(data):
    channels = int(np.max(data['gate_noise'])) + 1

    def features(prefix):
        output = np.zeros((len(data[prefix + '_observable']), channels + 1))
        for position, (begin, end, observable) in enumerate(zip(
                data[prefix + '_ptr'][:-1], data[prefix + '_ptr'][1:],
                data[prefix + '_observable'])):
            weight = np.count_nonzero(observable)
            output[position, 0] = weight
            for gate in data[prefix + '_gates'][begin:end]:
                channel = data['gate_noise'][gate]
                if channel >= 0:
                    output[position, channel + 1] += weight
        return output

    matrix = features('train')
    contrast = np.clip(np.abs(2 * data['train_plus'] / data['train_shots'] - 1), 0.02, 0.99999)
    coefficients = nnls(matrix, -np.log(contrast))[0]
    query_values = []
    for begin, end in zip(data['query_ptr'][:-1], data['query_ptr'][1:]):
        value = 0.0
        for position in range(begin, end):
            channel = int(data['query_channel'][position])
            coefficient = coefficients[0] / 2 if channel < 0 else coefficients[channel + 1]
            value += data['query_coeff'][position] * np.count_nonzero(
                data['query_pauli'][position]) * coefficient
        query_values.append(value)
    count = len(query_values)
    return {'structural_identifiable': np.ones(count), 'calibration_identifiable': np.ones(count),
            'query_log_estimate': np.array(query_values),
            'holdout_mean': ideal_signs(data, 'holdout') * np.exp(-features('holdout') @ coefficients)}


if __name__ == '__main__':
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    np.savez_compressed(sys.argv[2], **solve(data))

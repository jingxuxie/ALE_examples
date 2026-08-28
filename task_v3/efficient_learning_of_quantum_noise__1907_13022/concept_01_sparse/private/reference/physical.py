import numpy as np


def characters(error_paulis, observable_paulis):
    errors = np.asarray(error_paulis, dtype=np.uint8)
    observables = np.asarray(observable_paulis, dtype=np.uint8)
    parity = np.zeros((len(observables), len(errors)), dtype=np.uint8)
    for qubit in range(errors.shape[1]):
        left = observables[:, qubit, None]
        right = errors[None, :, qubit]
        parity ^= ((left != 0) & (right != 0) & (left != right)).astype(np.uint8)
    return 1.0 - 2.0 * parity


def spectrum(paulis, probabilities, p_identity, observables):
    return p_identity + characters(paulis, observables) @ probabilities


def masks_to_observables(masks):
    result = np.zeros((len(masks), masks.shape[1] // 2), dtype=np.uint8)
    first = masks[:, 0::2]
    second = masks[:, 1::2]
    result[(second == 1) & (first == 0)] = 1
    result[(second == 1) & (first == 1)] = 2
    result[(second == 0) & (first == 1)] = 3
    return result

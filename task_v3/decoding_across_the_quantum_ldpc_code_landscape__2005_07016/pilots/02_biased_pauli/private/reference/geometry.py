import numpy as np

PAULIS = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
CLIFFORDS = np.array([[[1, 0], [0, 1]], [[0, 1], [1, 0]],
                     [[1, 0], [1, 1]], [[1, 1], [0, 1]],
                     [[0, 1], [1, 1]], [[1, 1], [1, 0]]], dtype=np.uint8)


def transport(error_x, error_z, frame, permutation):
    physical_x = np.empty_like(error_x)
    physical_z = np.empty_like(error_z)
    physical_x[..., permutation] = ((error_x * frame[:, 0, 0])
                                    ^ (error_z * frame[:, 0, 1]))
    physical_z[..., permutation] = ((error_x * frame[:, 1, 0])
                                    ^ (error_z * frame[:, 1, 1]))
    return physical_x, physical_z


def canonical_probabilities(case):
    frame = case['frame']
    mapped = np.einsum('nij,kj->nki', frame, PAULIS) % 2
    labels = np.array([[0, 3], [1, 2]])[mapped[:, :, 0], mapped[:, :, 1]]
    return np.take_along_axis(case['pauli_probs'][case['permutation']], labels, axis=1)


def physical_generators(code, frame, permutation):
    base_x, base_z = code['base_hx'], code['base_hz']
    generator_x = np.concatenate((base_x, np.zeros_like(base_z)), axis=0)
    generator_z = np.concatenate((np.zeros_like(base_x), base_z), axis=0)
    return transport(generator_x, generator_z, frame, permutation)


def physical_logicals(code, frame, permutation):
    logical_x, logical_z = code['lx'], code['lz']
    operators_x = np.concatenate((logical_x, np.zeros_like(logical_z)))
    operators_z = np.concatenate((np.zeros_like(logical_x), logical_z))
    return transport(operators_x, operators_z, frame, permutation)


def pairing(error_x, error_z, operator_x, operator_z):
    return (error_x @ operator_z.T + error_z @ operator_x.T) % 2


def assess(case, truth, correction_x, correction_z):
    syndrome_ok = np.all(pairing(correction_x, correction_z, case['gx'], case['gz'])
                         == case['syndrome'], axis=1)
    logical_ok = np.all(pairing(correction_x, correction_z, truth['logical_x'],
                               truth['logical_z']) == truth['logical_signature'], axis=1)
    success = syndrome_ok & logical_ok
    return {'success_count': int(success.sum()), 'shots': len(success),
            'raw_logical_success': float(success.mean()),
            'consistency': float(syndrome_ok.mean()),
            'consistent_count': int(syndrome_ok.sum())}

import json
from functools import reduce
from pathlib import Path

import numpy as np
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'source' / 'upstream'
PUBLIC = ROOT / 'participant' / 'v_01' / 'input'
IDENTITY = np.eye(2)
PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]])
PAULI_Z = np.diag([1, -1]).astype(complex)


def tensor(*operators):
    return reduce(np.kron, operators)


def spin_operators():
    exchange = []
    for bond in range(3):
        operator = np.zeros((16, 16), dtype=complex)
        for pauli in (PAULI_X, PAULI_Y, PAULI_Z):
            factors = [IDENTITY] * 4
            factors[bond] = pauli
            factors[bond + 1] = pauli
            operator += tensor(*factors) / 4
        exchange.append(operator)
    fields = []
    for coefficients in ([-3, 1, 1, 1], [-2, -2, 2, 2], [-1, -1, -1, 3]):
        operator = np.zeros((16, 16), dtype=complex)
        for site, coefficient in enumerate(coefficients):
            factors = [IDENTITY] * 4
            factors[site] = PAULI_Z
            operator += coefficient * tensor(*factors) / 8
        fields.append(operator)
    selected = [3, 5, 6, 9, 10, 12]
    operators = np.array([operator[np.ix_(selected, selected)] for operator in exchange + fields])
    operators -= np.trace(operators, axis1=1, axis2=2)[:, None, None] * np.eye(6)[None] / 6
    return operators


def actual_device(gate):
    data = loadmat(SOURCE / 'examples' / 'data' / f'{gate}.mat')
    operators = spin_operators()
    exchange = np.exp(data['eps']).T
    sensitivity = np.concatenate([exchange, np.ones_like(exchange)], axis=1)
    coefficients = np.concatenate([exchange, np.broadcast_to(data['B'], exchange.shape)], axis=1)
    return dict(dt=data['t'].ravel(), H=np.einsum('sa,aij->sij', coefficients, operators),
                operators=operators, sensitivity=sensitivity,
                blocks=np.array([0, len(exchange)]), computational=np.array([1, 2, 3, 4]))


def actual_single(gate, duration_scale=1.0):
    data = loadmat(SOURCE / 'examples' / 'data' / f'{gate}.mat')
    exchange = np.exp(data['eps'][0])
    hamiltonian = (exchange[:, None, None] * PAULI_X + data['B'][0, 0] * PAULI_Z) / 2
    return dict(dt=data['t'].ravel() * duration_scale, H=hamiltonian / duration_scale,
                operators=np.array([PAULI_X / 2, PAULI_Z / 2]),
                sensitivity=np.ones((len(exchange), 2)),
                blocks=np.array([0, len(exchange)]), computational=np.arange(2))


def repeat_arrays(arrays, count):
    segments = len(arrays['dt'])
    return {key: np.concatenate([value] * count) if key in ('dt', 'H', 'sensitivity')
            else np.arange(count + 1) * segments if key == 'blocks' else value
            for key, value in arrays.items()}


def driven_static(shift=False):
    if shift:
        duration = np.array([0.6, 1.2, 0.4, 0.9, 0.55])
        coefficients = np.array([[0.6, 0.2, 0.3], [-0.1, 1.1, 0.1], [0.5, 0.2, -0.4],
                                 [-0.8, 0.3, 0.1], [0.2, -0.4, 0.6]])
    else:
        duration = np.array([1.1, 0.8, 0.9, 0.7])
        coefficients = np.array([[0.65, 0, 0.3], [0, 1.1, 0], [-0.5, 0, 0.25], [0.2, 0.7, 0.1]])
    return dict(dt=duration, H=np.einsum('sa,aij->sij', coefficients,
                                        [PAULI_X, PAULI_Y, PAULI_Z]),
                operators=np.array([PAULI_Z / 2, PAULI_X / 2]),
                sensitivity=np.column_stack([np.ones(len(duration)), np.linspace(0.7, 1.1, len(duration))]),
                blocks=np.arange(len(duration) + 1), computational=np.arange(2))


def qutrit():
    lower = np.diag(np.sqrt([1, 2]), 1)
    drive_x = (lower + lower.T) / 2
    drive_y = (lower - lower.T) / 2j
    detuning = np.diag([0, 1, 2])
    durations = np.array([0.45, 0.6, 0.3, 0.7, 0.55, 0.4])
    controls = [(0.8, 0.1), (0.3, 0.7), (-0.5, 0.2), (0.2, -0.6), (0.5, 0.3), (-0.2, -0.5)]
    hamiltonians = np.array([0.22 * detuning + np.diag([0, 0, -0.9]) + real * drive_x + imag * drive_y
                            for real, imag in controls])
    return dict(dt=durations, H=hamiltonians,
                operators=np.array([detuning - np.eye(3), drive_x]),
                sensitivity=np.column_stack([np.ones(6), [0.7, 0.9, 1.1, 0.8, 0.6, 1.0]]),
                blocks=np.array([0, 2, 4, 6]), computational=np.array([0, 1]))


def echo(shift=False):
    angles = [0, np.pi, 0, np.pi, 0] if not shift else [0, np.pi, 0, np.pi, 0, np.pi, 0, np.pi, 0]
    durations = np.array([0.75 if index % 2 == 0 else 0.12 for index in range(len(angles))])
    hamiltonians = np.array([(angle / (2 * duration)) * (PAULI_X if index % 4 == 1 else PAULI_Y)
                            + 0.12 * PAULI_Z for index, (angle, duration) in enumerate(zip(angles, durations))])
    return dict(dt=durations, H=hamiltonians, operators=np.array([PAULI_Z / 2]),
                sensitivity=np.ones((len(durations), 1)), blocks=np.arange(len(durations) + 1),
                computational=np.arange(2))


def write_case(directory, name, arrays, noise, family, origin):
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(directory / f'{name}.npz', **arrays)
    metadata = dict(case_id=name, asset=f'{name}.npz', noise=noise,
                    device_notes=origin)
    (directory / f'{name}.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return dict(case_id=name, family=family, file=f'{name}.json')


def main():
    cases = PUBLIC / 'cases'
    hidden = ROOT / 'evaluator' / 'hidden' / 'cases'
    real = PUBLIC / 'real_controls'
    real.mkdir(parents=True, exist_ok=True)
    for gate in ('X2ID', 'Y2ID', 'CNOT'):
        data = loadmat(SOURCE / 'examples' / 'data' / f'{gate}.mat')
        np.savez_compressed(real / f'{gate}.npz', eps=data['eps'], dt=data['t'].ravel(), B=data['B'].ravel())
    public_index = []
    public_index.append(write_case(cases, 'calibration_static',
                       dict(dt=np.array([1.0]), H=np.zeros((1, 2, 2)), operators=np.array([PAULI_Z / 2]),
                            sensitivity=np.ones((1, 1)), blocks=np.array([0, 1]), computational=np.arange(2)),
                       dict(kind='static', mixing=[[1]], sigma=[0.4]), 'commuting_calibration', 'Idle spin.'))
    public_index.append(write_case(cases, 'driven_static', driven_static(),
                       dict(kind='static', mixing=[[1, 0.4], [-0.3, 1]], sigma=[0.55, 0.32]),
                       'static_driven', 'Noncommuting finite-width control sequence.'))
    public_index.append(write_case(cases, 'memory_ou', repeat_arrays(actual_single('X2ID', 0.2), 2),
                       dict(kind='ou', mixing=[[1, 0.2], [-0.25, 1]], sigma=[0.6, 0.35], rates=[0.4, 1.4]),
                       'gaussian_memory', 'Two optimized one-qubit primitives, time-rescaled without changing ideal action.'))
    public_index.append(write_case(cases, 'switching_echo', echo(),
                       dict(kind='telegraph', mixing=[[1]], sigma=[0.95], rates=[0.35]),
                       'switching', 'Finite-width echo with residual longitudinal drift.'))
    public_index.append(write_case(cases, 'white_gate', actual_single('Y2ID'),
                       dict(kind='white', mixing=[[1, 0.3], [0.2, 1]], sigma=[0.10, 0.07]),
                       'white', 'Optimized one-qubit primitive.'))
    broadband = dict(kind='broadband', mixing=np.vstack([np.ones(7),
                    np.linspace(-0.3, 0.5, 7), np.linspace(0.4, -0.2, 7), np.zeros((3, 7))]).tolist(),
                    sigma=(2e-4 * np.geomspace(0.3, 2.0, 7)).tolist(),
                    rates=np.geomspace(0.004, 12, 7).tolist())
    public_index.append(write_case(cases, 'broadband_entangler', actual_device('CNOT'), broadband,
                       'broadband', 'Full six-state optimized exchange entangler with weak correlated charge noise.'))
    static_device = dict(kind='static', mixing=[[1, 0], [0.3, 0.5], [-0.1, 0.7],
                                              [0.15, -0.1], [0, 0], [0.1, 0.2]], sigma=[0.018, 0.012])
    public_index.append(write_case(cases, 'leakage_static', actual_device('X2ID'), static_device,
                       'leakage', 'Six-state optimized local rotation with correlated detuning and field offsets.'))
    hidden_index = []
    hidden_index.append(write_case(hidden, 'held_static', driven_static(True),
                       dict(kind='static', mixing=[[0.8, -0.6], [0.4, 0.7]], sigma=[0.7, 0.48]),
                       'static_driven', 'Shifted noncommuting drive with rotated noise axes.'))
    hidden_index.append(write_case(hidden, 'held_ou', qutrit(),
                       dict(kind='ou', mixing=[[1, 0.25], [-0.2, 1]], sigma=[0.6, 0.45], rates=[0.55, 1.6]),
                       'gaussian_memory', 'Anharmonic ladder with colored detuning and transverse coupling.'))
    hidden_index.append(write_case(hidden, 'held_switching', echo(True),
                       dict(kind='telegraph', mixing=[[1]], sigma=[1.3], rates=[0.22]),
                       'switching', 'Two-axis finite-width decoupling with slow switching.'))
    white_arrays = qutrit()
    white_arrays['blocks'] = np.arange(len(white_arrays['dt']) + 1)
    hidden_index.append(write_case(hidden, 'held_white', white_arrays,
                       dict(kind='white', mixing=[[0.8, -0.2], [0.5, 1]], sigma=[0.4, 0.3]),
                       'white', 'White-noise anharmonic device with arbitrary segment partition.'))
    broad_hidden = dict(kind='broadband', rates=np.geomspace(0.002, 18, 9).tolist(),
                        sigma=(2.5e-4 * np.geomspace(0.25, 2.1, 9)).tolist(),
                        mixing=np.vstack([np.linspace(-0.4, 0.6, 9), np.ones(9),
                                          np.linspace(0.5, -0.25, 9), np.zeros((3, 9))]).tolist())
    hidden_index.append(write_case(hidden, 'held_broadband', repeat_arrays(actual_device('Y2ID'), 2),
                       broad_hidden, 'broadband', 'Repeated real six-state device under weak multiscale charge noise.'))
    hidden_index.append(write_case(hidden, 'held_leakage', actual_device('CNOT'),
                       dict(kind='static', mixing=[[1], [-0.45], [0.7], [0.12], [0], [-0.15]], sigma=[0.035]),
                       'leakage', 'Full entangling pulse including physically accessible leakage states.'))
    (PUBLIC / 'manifest.json').write_text(json.dumps(public_index, indent=2) + '\n')
    (ROOT / 'evaluator' / 'hidden' / 'manifest.json').write_text(json.dumps(hidden_index, indent=2) + '\n')


if __name__ == '__main__':
    main()

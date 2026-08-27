import json
from pathlib import Path

import numpy as np
from scipy.linalg import expm


def load_case(path):
    path = Path(path)
    case = json.loads(path.read_text())
    arrays = dict(np.load(path.parent / case['asset'], allow_pickle=False))
    return case, arrays


def liouvillian(operator):
    dimension = operator.shape[-1]
    identity = np.eye(dimension)
    return -1j * (np.kron(identity, operator) - np.kron(operator.T, identity))


def ideal_channel(arrays):
    dimension = arrays['H'].shape[-1]
    propagator = np.eye(dimension, dtype=complex)
    for duration, hamiltonian in zip(arrays['dt'], arrays['H']):
        propagator = expm(-1j * duration * hamiltonian) @ propagator
    return np.kron(propagator.conj(), propagator)


def time_noise(arrays):
    return arrays['sensitivity'][:, :, None, None] * arrays['operators'][None]


def choi(channel):
    dimension = int(round(np.sqrt(channel.shape[0])))
    return channel.reshape((dimension,) * 4, order='F').transpose(0, 2, 1, 3).reshape(
        (dimension ** 2, dimension ** 2), order='F') / dimension


def observables(channel, arrays):
    dimension = arrays['H'].shape[-1]
    ideal = ideal_channel(arrays)
    error = ideal.conj().T @ channel
    identity = np.eye(dimension).reshape(-1, order='F')
    computational = arrays.get('computational', np.arange(dimension)).astype(int)
    state = np.zeros((dimension, dimension), dtype=complex)
    state[computational, computational] = 1 / len(computational)
    final = (channel @ state.reshape(-1, order='F')).reshape((dimension, dimension), order='F')
    choi_matrix = choi(channel)
    return {
        'infidelity': float(1 - np.trace(error).real / dimension ** 2),
        'leakage': float(1 - final[computational, computational].real.sum()),
        'coherent_size': float(np.linalg.norm(error - error.conj().T) / 2),
        'tp_error': float(np.linalg.norm(identity.conj() @ channel - identity.conj())),
        'unital_error': float(np.linalg.norm(channel @ identity - identity)),
        'choi_min': float(np.linalg.eigvalsh((choi_matrix + choi_matrix.conj().T) / 2).min()),
    }


def spectral_density(law, omega):
    mixing = np.asarray(law['mixing'], dtype=float)
    sigma = np.asarray(law['sigma'], dtype=float)
    kind = law['kind']
    if kind == 'white':
        latent = np.broadcast_to(sigma[:, None] ** 2, (len(sigma), len(omega)))
    else:
        if kind == 'static':
            rates = np.full(len(sigma), law.get('regularization', 0.002))
        else:
            rates = np.asarray(law['rates'], dtype=float)
        if kind == 'telegraph':
            rates = 2 * rates
        latent = 2 * sigma[:, None] ** 2 * rates[:, None] / (
            rates[:, None] ** 2 + omega[None] ** 2)
    return np.einsum('am,bm,mw->abw', mixing, mixing, latent)


def make_pulse(arrays):
    import filter_functions as ff

    basis = ff.Basis.ggm(arrays['H'].shape[-1])
    coefficients = np.einsum('kij,sji->ks', basis, arrays['H']).real
    nonzero = np.max(np.abs(coefficients), axis=1) > 1e-14
    control = [[operator, coefficient, f'control_{index:03d}'] for index, (operator, coefficient)
               in enumerate(zip(basis[nonzero], coefficients[nonzero]))]
    if not control:
        control = [[np.eye(arrays['H'].shape[-1]), np.zeros(len(arrays['dt'])), 'zero']]
    noise = [[operator, arrays['sensitivity'][:, index], f'noise_{index:03d}']
             for index, operator in enumerate(arrays['operators'])]
    return ff.PulseSequence(control, noise, arrays['dt'], basis=basis)


def basis_transform(basis):
    return np.stack([operator.reshape(-1, order='F') for operator in basis], axis=1)


def subset(arrays, begin, end):
    return {key: value[begin:end] if key in ('dt', 'H', 'sensitivity') else value
            for key, value in arrays.items()}

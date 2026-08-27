import json
from pathlib import Path

import numpy as np
from scipy.linalg import expm


IDENTITY = np.eye(2, dtype=complex)
SIGMA_X = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_Z = np.diag([1, -1]).astype(complex)
LOWERING = np.array([[0, 1], [0, 0]], dtype=complex)


def pure(vector):
    vector = np.asarray(vector, dtype=complex)
    vector /= np.linalg.norm(vector)
    return np.outer(vector, vector.conj())


def thermal(eta, temperature=0.0, cutoff=25.0):
    return {'kind': 'thermal', 'eta': eta, 'temperature': temperature, 'cutoff': cutoff}


def waveform(kind, **parameters):
    return {'kind': kind, **parameters}


def make_case(identifier, family, physics, hamiltonian, initial, observables, times,
              h_ops=(), h_coeffs=(), c_ops=(), c_coeffs=(), a_ops=(), baths=(), **extra):
    dimension = len(hamiltonian)
    arrays = {'H0': np.asarray(hamiltonian, dtype=complex), 'rho0': initial,
              'e_ops': np.asarray(observables), 'times': np.asarray(times)}
    for name, operators in [('h_ops', h_ops), ('c_ops', c_ops), ('a_ops', a_ops)]:
        arrays[name] = np.asarray(operators, dtype=complex).reshape(-1, dimension, dimension)
    metadata = {'id': identifier, 'family': family, 'physics': physics,
                'arrays': identifier + '.npz', 'h_coeffs': list(h_coeffs),
                'c_coeffs': list(c_coeffs), 'baths': list(baths), **extra}
    return metadata, arrays


def rotate(arrays, seed):
    random = np.random.default_rng(seed)
    dimension = len(arrays['H0'])
    raw = random.normal(size=(dimension, dimension)) + 1j * random.normal(size=(dimension, dimension))
    unitary = expm(0.4j * (raw + raw.conj().T))
    for name in ['H0', 'rho0', 'e_ops', 'h_ops', 'a_ops', 'c_ops']:
        arrays[name] = unitary @ arrays[name] @ unitary.conj().T


def cases(hidden=False):
    drive = 2 * np.pi
    offset = 0.237 if hidden else 0.0
    times = offset + np.linspace(0, 40 if hidden else 18, 121) ** 1.03
    spin = make_case('spectroscopy_spin', 'driven_broadband_spin', 'floquet',
        -drive * SIGMA_Z / 2 + 0.11 * SIGMA_X, pure([1, 0.3j]),
        [np.diag([0, 1]), SIGMA_X, SIGMA_Y], times,
        h_ops=[SIGMA_X, SIGMA_Z],
        h_coeffs=[waveform('sin', amplitude=2.9 if hidden else 0.2 * drive, omega=drive, phase=0.2),
                  waveform('cos', amplitude=0.8 if hidden else 0.1, omega=2 * drive, phase=0.6)],
        a_ops=[SIGMA_X, SIGMA_Z], baths=[thermal(0.035, 0.45 if hidden else 0), thermal(0.012, 0.7)], period=1.0)
    if hidden:
        rotate(spin[1], 812)
    yield spin

    dimension = 5 if hidden else 3
    annihilation = np.diag(np.sqrt(np.arange(1, dimension)), 1).astype(complex)
    number = annihilation.conj().T @ annihilation
    ladder_initial = np.zeros(dimension, dtype=complex)
    ladder_initial[:3] = [1, 0.6j, -0.3]
    bath = {'kind': 'filtered', 'eta': 0.04, 'temperature': 0.85, 'cutoff': 35,
            'center': 8.4 if hidden else 5.7, 'width': 0.35, 'floor': 0.025}
    ladder = make_case('spectroscopy_ladder', 'filtered_multilevel_drive', 'floquet',
        4.7 * number + 0.23 * number @ number, pure(ladder_initial),
        [number / (dimension - 1), annihilation + annihilation.conj().T,
         1j * (annihilation - annihilation.conj().T)],
        offset + np.r_[0, np.geomspace(0.07, 2600 if hidden else 160, 95)],
        h_ops=[annihilation + annihilation.conj().T, number],
        h_coeffs=[waveform('cos', amplitude=3.8 if hidden else 1.2, omega=drive, phase=1.1),
                  waveform('sin', amplitude=1.7 if hidden else 0.6, omega=3 * drive)],
        a_ops=[annihilation + annihilation.conj().T, number], baths=[bath, thermal(0.006, 1.1)], period=1.0)
    if hidden:
        rotate(ladder[1], 931)
    yield ladder

    hamiltonian = np.diag([0, 2.0, 2.0]).astype(complex)
    common = np.array([[0, 1, -1j if hidden else 1], [1, 0, 0], [1j if hidden else 1, 0, 0]], dtype=complex)
    collective = make_case('collective_decay', 'degenerate_common_bath', 'redfield',
        hamiltonian, pure([0.4j, 1, 0.25j if hidden else -0.5]),
        [np.diag([0, 1, 1]), np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]]),
         np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]])],
        offset + np.r_[0, np.geomspace(0.02, 90, 99)],
        a_ops=[common, np.diag([0, 1, 1])], baths=[thermal(0.09, 0.25), {'kind': 'flat', 'strength': 0.013}], secular=True)
    if hidden:
        rotate(collective[1], 59)
    yield collective

    first_x, second_x = np.kron(SIGMA_X, IDENTITY), np.kron(IDENTITY, SIGMA_X)
    first_z, second_z = np.kron(SIGMA_Z, IDENTITY), np.kron(IDENTITY, SIGMA_Z)
    first_y = np.kron(SIGMA_Y, IDENTITY)
    coupled = make_case('coupled_spins', 'nonsecular_coupled_baths', 'redfield',
        2.4 * first_z + 2.37 * second_z + 0.17 * first_x + (0.12 if hidden else 0.35) * first_x @ second_x,
        pure(np.kron([0.8, 0.2j], [0.2, 0.8])), [first_z, first_x, first_y],
        offset + np.linspace(0, 22 if hidden else 14, 133) ** 1.04,
        a_ops=[first_x + (0.45 if hidden else 0.0) * second_x, second_x],
        baths=[thermal(0.055, 1.8 if hidden else 0.3),
               {'kind': 'filtered', 'eta': 0.08, 'temperature': 0.55, 'cutoff': 25,
                'center': 4.8, 'width': 0.7, 'floor': 0.1}], secular=False)
    if hidden:
        rotate(coupled[1], 512)
    yield coupled

    dimension = 96 if hidden else 32
    annihilation = np.diag(np.sqrt(np.arange(1, dimension)), 1).astype(complex)
    number = annihilation.conj().T @ annihilation
    state = np.zeros(dimension, dtype=complex)
    state[:5] = [1, 0.8j, -0.4, 0.18j, 0.03]
    resonator = make_case('thermal_resonator', 'pulsed_thermal_resonator', 'lindblad',
        0.12 * number + 0.0008 * number @ number, pure(state),
        [number, annihilation + annihilation.conj().T, 1j * (annihilation - annihilation.conj().T)],
        0.0 + np.unique(np.r_[np.linspace(0, 8, 83), 1.31, 1.35, 1.38, 3.08, 3.14]),
        h_ops=[annihilation + annihilation.conj().T, 1j * (annihilation - annihilation.conj().T)],
        h_coeffs=[waveform('gaussian', amplitude=3.1 if hidden else 2.1, center=3.1, width=0.13),
                  waveform('steps', edges=[1.31, 1.38, 4.7], values=[0, 3.7, -0.04, 0.25])],
        c_ops=[annihilation, annihilation.conj().T, number / np.sqrt(dimension)],
        c_coeffs=[waveform('decay', amplitude=0.6, offset=0.17, rate=0.3),
                  waveform('carrier', amplitude=[0.19, 0.09], offset=0.11, omega=1.7),
                  waveform('steps', edges=[2.3, 3.7], values=[0.08, 0.31, 0.12])],
        scaling_sizes=[8, 16, 32] if not hidden else [])
    yield resonator

    gate_duration = np.pi / (4 * 2 * np.pi)
    first_lower = np.kron(LOWERING, IDENTITY)
    second_lower = np.kron(IDENTITY, LOWERING)
    gate = make_case('noisy_gate', 'two_qubit_process', 'lindblad',
        2 * np.pi * (first_x @ second_x + np.kron(SIGMA_Y, SIGMA_Y)) + 0.7 * first_z,
        pure([0, 1, 0.2j, 0]), [first_z, second_z, first_y],
        0.11 + gate_duration * np.linspace(0, 1, 51) ** 1.12,
        h_ops=[first_y], h_coeffs=[waveform('cos', amplitude=1.5, omega=18.0, phase=0.2)],
        c_ops=[first_lower, first_lower.conj().T, second_lower, second_lower.conj().T, first_z],
        c_coeffs=[waveform('constant', value=np.sqrt(0.75 * 2.5)),
                  waveform('constant', value=np.sqrt(0.75 * 1.5)),
                  waveform('decay', amplitude=1.1, rate=2.0),
                  waveform('constant', value=0.7), waveform('sin', amplitude=0.2, offset=0.3, omega=12)], process=True)
    if hidden:
        rotate(gate[1], 8126)
    yield gate


def write_cases(destination, hidden=False):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for metadata, arrays in cases(hidden):
        (destination / (metadata['id'] + '.json')).write_text(json.dumps(metadata, indent=2))
        np.savez_compressed(destination / metadata['arrays'], **arrays)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    write_cases(root / 'participant' / 'v_01' / 'input')
    write_cases(Path(__file__).parent / 'hidden', hidden=True)

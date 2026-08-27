import copy
import json
import unittest
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.special import jv

from oqs.baths import spectrum
from oqs.engine import solve
from oqs.io import load_case
from oqs.operators import coherent_generator, dissipator
from oqs.process import channel_to_choi
from oqs.spectral import redfield_generator


OPTIONS = json.loads((Path(__file__).parents[1] / 'configs.json').read_text())['production']
EVIDENCE = []


def empty_case(dimension=2):
    return {'id': 'test', 'family': 'analytic', 'physics': 'lindblad',
            'H0': np.zeros((dimension, dimension), complex),
            'h_ops': np.empty((0, dimension, dimension), complex),
            'c_ops': np.empty((0, dimension, dimension), complex),
            'a_ops': np.empty((0, dimension, dimension), complex),
            'h_coeffs': [], 'c_coeffs': [], 'baths': [],
            'rho0': np.ones((dimension, dimension), complex) / dimension,
            'e_ops': np.eye(dimension, dtype=complex)[None],
            'times': np.array([0.23, 0.231, 0.33, 0.78, 1.8])}


def rotation(dimension, seed=71):
    random = np.random.default_rng(seed)
    matrix = random.normal(size=(dimension, dimension)) + 1j * random.normal(size=(dimension, dimension))
    return np.linalg.qr(matrix)[0]


def rotated_case(case, unitary):
    transformed = copy.deepcopy(case)
    for name in ['H0', 'rho0', 'h_ops', 'c_ops', 'a_ops', 'e_ops']:
        transformed[name] = unitary @ case[name] @ unitary.conj().T
    return transformed


class QualificationTests(unittest.TestCase):
    def assert_close(self, actual, expected, tolerance=1e-8):
        error = float(np.max(np.abs(actual - expected)))
        EVIDENCE.append({'test': self.id(), 'maximum_absolute_error': error,
                         'tolerance': tolerance, 'passed': error < tolerance})
        self.assertLess(error, tolerance, 'maximum absolute error: %.12g' % error)

    def test_complex_amplitude_damping_channel(self):
        case = empty_case()
        case['H0'] = np.diag([0.0, 1.3]).astype(complex)
        case['c_ops'] = np.array([[[0, 1], [0, 0]]], complex)
        case['c_coeffs'] = [{'kind': 'constant', 'value': [0.4, 0.7]}]
        case['process'] = True
        result = solve(case, OPTIONS)
        delay = case['times'] - case['times'][0]
        survival = np.exp(-0.65 * delay)
        expected = np.zeros_like(result['states'])
        expected[:, 1, 1] = survival / 2
        expected[:, 0, 0] = 1 - survival / 2
        expected[:, 0, 1] = np.sqrt(survival) * np.exp(1.3j * delay) / 2
        expected[:, 1, 0] = expected[:, 0, 1].conj()
        self.assert_close(result['states'], expected)
        phase = np.exp(-1.3j * delay[-1])
        no_jump = np.diag([1, np.sqrt(survival[-1]) * phase])
        jump = np.array([[0, np.sqrt(1 - survival[-1])], [0, 0]])
        channel = np.kron(no_jump.conj(), no_jump) + np.kron(jump.conj(), jump)
        self.assert_close(result['channel'], channel)
        choi = sum(np.outer(operator.ravel(order='F'), operator.ravel(order='F').conj())
                   for operator in [no_jump, jump])
        self.assert_close(result['choi'], choi)
        self.assert_close(result['channel'] @ case['rho0'].ravel(order='F'), expected[-1].ravel(order='F'))
        self.assert_close(np.trace(result['choi']), 2)

    def test_absolute_time_carrier(self):
        case = empty_case()
        case['c_ops'] = np.array([[[0, 1], [0, 0]]], complex)
        amplitude, offset, frequency, phase = 0.3 + 0.2j, 0.17, 2.7, 0.51
        case['c_coeffs'] = [{'kind': 'carrier', 'amplitude': [amplitude.real, amplitude.imag],
                             'offset': offset, 'omega': frequency, 'phase': phase}]
        times = case['times']
        primitive = lambda time: ((abs(amplitude) ** 2 + offset ** 2) * time
                                  + 2 * np.real(offset * amplitude * np.exp(1j * (frequency * time + phase)) / (1j * frequency)))
        integral = primitive(times) - primitive(times[0])
        result = solve(case, OPTIONS)
        self.assert_close(result['states'][:, 1, 1], np.exp(-integral) / 2)
        self.assert_close(result['states'][:, 0, 1], np.exp(-integral / 2) / 2)

    def test_unresolved_step_pulse(self):
        case = empty_case()
        case['times'] = np.array([0.1, 0.15, 0.9, 1.0])
        case['h_ops'] = np.array([np.diag([0, 1])], complex)
        case['h_coeffs'] = [{'kind': 'steps', 'edges': [0.511, 0.512], 'values': [0, 100, 0]}]
        result = solve(case, OPTIONS)
        self.assert_close(result['states'][-1, 0, 1], 0.5 * np.exp(0.1j))

    def test_unresolved_gaussian_pulse(self):
        case = empty_case()
        case['times'] = np.array([0.0, 0.8, 1.0])
        case['h_ops'] = np.array([np.diag([0, 1])], complex)
        case['h_coeffs'] = [{'kind': 'gaussian', 'center': 0.517, 'width': 0.0002, 'amplitude': 1200}]
        result = solve(case, OPTIONS)
        area = 1200 * 0.0002 * np.sqrt(2 * np.pi)
        self.assert_close(result['states'][-1, 0, 1], 0.5 * np.exp(1j * area))

    def test_static_thermal_gibbs(self):
        case = empty_case(3)
        case['physics'] = 'redfield'
        case['H0'] = np.diag([0, 1.2, 3.7]).astype(complex)
        case['a_ops'] = np.array([[[0.4, 1j, 0.3], [-1j, 0, 0.7j], [0.3, -0.7j, -0.2]]])
        case['baths'] = [{'kind': 'thermal', 'eta': 0.2, 'temperature': 0.8, 'cutoff': 20}]
        populations = np.exp(-np.diag(case['H0']).real / 0.8)
        case['rho0'] = np.diag(populations / populations.sum()).astype(complex)
        for secular in [False, True]:
            case['secular'] = secular
            result = solve(case, OPTIONS)
            self.assert_close(result['states'], case['rho0'])

    def test_nonsecular_white_noise_limit(self):
        case = empty_case(3)
        case['physics'] = 'redfield'
        case['H0'] = np.diag([0, 1.2, 3.7]).astype(complex)
        operator = np.array([[0.4, 1j, 0.3], [-1j, 0, 0.7j], [0.3, -0.7j, -0.2]])
        case['a_ops'] = operator[None]
        case['baths'] = [{'kind': 'flat', 'strength': 0.17}]
        actual, basis = redfield_generator(case)
        expected = coherent_generator(case['H0']) + 0.17 * dissipator(operator)
        self.assert_close(actual, expected, 1e-13)

    def test_secular_two_level_rates(self):
        case = empty_case()
        gap, transition = 2.3, 0.7 + 0.4j
        case['H0'] = np.diag([0, gap]).astype(complex)
        case['a_ops'] = np.array([[[0.3, transition], [transition.conjugate(), -0.2]]])
        bath = {'kind': 'thermal', 'eta': 0.12, 'temperature': 0.9, 'cutoff': 20}
        case['baths'], case['physics'], case['secular'] = [bath], 'redfield', True
        delay = case['times'] - case['times'][0]
        down = float(spectrum(bath, gap)) * abs(transition) ** 2
        up = float(spectrum(bath, -gap)) * abs(transition) ** 2
        equilibrium = up / (down + up)
        excited = equilibrium + (0.5 - equilibrium) * np.exp(-(down + up) * delay)
        coherence = 0.5 * np.exp((1j * gap - (down + up) / 2 - 0.125 * spectrum(bath, 0)) * delay)
        result = solve(case, OPTIONS)
        self.assert_close(result['states'][:, 1, 1], excited, 1e-12)
        self.assert_close(result['states'][:, 0, 1], coherence, 1e-12)

    def test_independent_degenerate_baths(self):
        case = empty_case(3)
        case['physics'], case['secular'] = 'redfield', True
        case['H0'] = np.diag([0, 2, 2]).astype(complex)
        case['a_ops'] = np.array([[[0, 1, 0], [1, 0, 0], [0, 0, 0]],
                                  [[0, 0, 1j], [0, 0, 0], [-1j, 0, 0]]], complex)
        bath = {'kind': 'thermal', 'eta': 0.2, 'temperature': 0, 'cutoff': 20}
        case['baths'] = [bath, bath]
        dark_for_common = np.array([0, -1j, 1]) / np.sqrt(2)
        case['rho0'] = np.outer(dark_for_common, dark_for_common.conj())
        result = solve(case, OPTIONS)
        survival = np.exp(-spectrum(bath, 2) * (case['times'] - case['times'][0]))
        self.assert_close(result['states'][:, 0, 0], 1 - survival, 1e-12)

    def test_floquet_exact_quasienergy_degeneracy(self):
        case = empty_case(3)
        case['H0'] = np.diag([0, 2 * np.pi, 2 * np.pi]).astype(complex)
        case['a_ops'] = np.array([[[0.4, 1j, 0.3], [-1j, 0.1, 0.7j], [0.3, -0.7j, -0.2]],
                                  [[0.2, 0.7, 0.1j], [0.7, -0.3, 0.4j], [-0.1j, -0.4j, 0.7]]])
        case['baths'] = [{'kind': 'thermal', 'eta': 0.04, 'temperature': 0.9, 'cutoff': 20},
                          {'kind': 'flat', 'strength': 0.017}]
        case['physics'], case['period'], case['secular'] = 'redfield', 1.0, True
        expected = solve(case, OPTIONS)
        case['physics'] = 'floquet'
        actual = solve(case, OPTIONS)
        self.assert_close(actual['states'], expected['states'])
        changed = solve(rotated_case(case, rotation(3)), dict(OPTIONS, branch_shifts=[-2, 0, 2]))
        self.assert_close(changed['states'], rotation(3) @ actual['states'] @ rotation(3).conj().T)

    def test_nonsecular_pair_sum(self):
        case = empty_case(3)
        case['physics'] = 'redfield'
        energies = np.array([0.0, 0.7, 1.31])
        case['H0'] = np.diag(energies).astype(complex)
        case['a_ops'] = np.array([[[0.4, 1j, 0.3], [-1j, 0, 0.7j], [0.3, -0.7j, -0.2]]])
        bath = {'kind': 'thermal', 'eta': 0.12, 'temperature': 0.8, 'cutoff': 20}
        case['baths'] = [bath]
        density = rotation(3) @ np.diag([0.2, 0.3, 0.5]) @ rotation(3).conj().T
        expected = -1j * (case['H0'] @ density - density @ case['H0'])
        transitions = []
        for row in range(3):
            for column in range(3):
                operator = np.zeros((3, 3), complex)
                operator[row, column] = case['a_ops'][0, row, column]
                transitions.append((float(spectrum(bath, energies[column] - energies[row])), operator))
        for left_rate, left in transitions:
            for right_rate, right in transitions:
                expected += ((left_rate + right_rate) * left @ density @ right.conj().T
                             - left_rate * right.conj().T @ left @ density
                             - right_rate * density @ right.conj().T @ left) / 2
        generator, basis = redfield_generator(case)
        self.assert_close((generator @ density.ravel()).reshape(3, 3), expected, 1e-13)

    def test_collective_dark_state(self):
        case = empty_case(3)
        case['physics'] = 'redfield'
        case['secular'] = True
        case['H0'] = np.diag([0, 2, 2]).astype(complex)
        case['a_ops'] = np.array([[[0, 1, 1j], [1, 0, 0], [-1j, 0, 0]]], complex)
        case['baths'] = [{'kind': 'thermal', 'eta': 0.2, 'temperature': 0, 'cutoff': 20}]
        dark = np.array([0, -1j, 1]) / np.sqrt(2)
        case['rho0'] = np.outer(dark, dark.conj())
        case['times'] = np.array([0, 1, 10, 100])
        result = solve(case, OPTIONS)
        self.assert_close(result['states'], case['rho0'])
        unitary = rotation(3)
        transformed = solve(rotated_case(case, unitary), OPTIONS)
        self.assert_close(transformed['states'], unitary @ result['states'] @ unitary.conj().T)

    def test_floquet_static_folded_spectrum(self):
        case = empty_case(3)
        case['H0'] = np.diag([0, 6.7, 12.9]).astype(complex)
        case['a_ops'] = np.array([[[0.4, 1j, 0.3], [-1j, 0, 0.7j], [0.3, -0.7j, -0.2]]])
        case['baths'] = [{'kind': 'thermal', 'eta': 0.07, 'temperature': 0.8, 'cutoff': 20}]
        case['physics'], case['period'], case['secular'] = 'redfield', 1.0, True
        case['times'] = np.array([0.23, 0.43, 5.42, 122.123, 5001.7])
        expected = solve(case, OPTIONS)
        case['physics'] = 'floquet'
        result = solve(case, OPTIONS)
        self.assert_close(result['states'], expected['states'])
        branched = solve(case, dict(OPTIONS, branch_shifts=[-2, 1, 3]))
        self.assert_close(branched['states'], result['states'])

    def test_floquet_distant_sideband(self):
        case = empty_case()
        case['H0'] = np.diag([0, 128 * 2 * np.pi + 0.7]).astype(complex)
        case['a_ops'] = np.array([[[0.2, 1j], [-1j, -0.3]]], complex)
        case['baths'] = [{'kind': 'thermal', 'eta': 0.0001, 'temperature': 0.9, 'cutoff': 2000}]
        case['physics'], case['period'], case['secular'] = 'redfield', 1.0, True
        expected = solve(case, OPTIONS)
        case['physics'] = 'floquet'
        actual = solve(case, OPTIONS)
        self.assert_close(actual['states'], expected['states'], 1e-8)
        self.assertGreaterEqual(actual['solver_retained_harmonics'], 128)

    def test_floquet_bessel_sidebands(self):
        case = empty_case()
        gap, amplitude, period = 4.7, 7.3, 1.0
        frequency = 2 * np.pi / period
        case['H0'] = np.diag([0, gap]).astype(complex)
        case['h_ops'] = np.array([np.diag([0, 1])], complex)
        case['h_coeffs'] = [{'kind': 'cos', 'amplitude': amplitude, 'omega': frequency}]
        case['a_ops'] = np.array([[[0.3, 1j], [-1j, -0.3]]], complex)
        bath = {'kind': 'filtered', 'eta': 0.08, 'temperature': 0.9, 'cutoff': 30,
                'center': 5.7, 'width': 0.4, 'floor': 0.03}
        case['baths'], case['physics'], case['period'] = [bath], 'floquet', period
        case['times'] = np.array([0.23, 0.43, 1.72, 5.41, 12.29, 50.13, 2501.19])
        harmonics = np.arange(-70, 71)
        weights = jv(harmonics, amplitude / frequency) ** 2
        down = np.sum(weights * spectrum(bath, gap + harmonics * frequency))
        up = np.sum(weights * spectrum(bath, -gap - harmonics * frequency))
        delays = case['times'] - case['times'][0]
        equilibrium = up / (down + up)
        excited = equilibrium + (0.5 - equilibrium) * np.exp(-(down + up) * delays)
        phase = gap * delays + amplitude / frequency * (np.sin(frequency * case['times']) - np.sin(frequency * case['times'][0]))
        coherence = 0.5 * np.exp(1j * phase - ((down + up) / 2 + 0.18 * spectrum(bath, 0)) * delays)
        expected = np.zeros((len(delays), 2, 2), complex)
        expected[:, 1, 1], expected[:, 0, 0] = excited, 1 - excited
        expected[:, 0, 1], expected[:, 1, 0] = coherence, coherence.conj()
        result = solve(case, OPTIONS)
        self.assert_close(result['states'], expected)

    def test_floquet_zero_bath_micromotion(self):
        case = empty_case()
        case['H0'] = np.array([[0.7, 0.1j], [-0.1j, -0.7]])
        case['h_ops'] = np.array([[[0, 1], [1, 0]]], complex)
        case['h_coeffs'] = [{'kind': 'sin', 'amplitude': 1.7, 'omega': 2 * np.pi, 'phase': 0.7}]
        case['times'] = np.array([1.37, 1.38, 1.45, 2.17, 5.141, 8.123])
        expected = solve(case, OPTIONS)
        case['physics'], case['period'] = 'floquet', 1.0
        actual = solve(case, OPTIONS)
        self.assert_close(actual['states'], expected['states'])

    def test_development_basis_covariance(self):
        inputs = Path(__file__).parents[2] / 'input'
        if not inputs.exists():
            self.skipTest('Development assets not adjacent to workspace')
        for filename in sorted(inputs.glob('*.json')):
            with self.subTest(case=filename.stem):
                case = load_case(filename)
                unitary = rotation(len(case['H0']))
                expected = solve(case, OPTIONS)
                actual = solve(rotated_case(case, unitary), OPTIONS)
                self.assert_close(actual['states'], unitary @ expected['states'] @ unitary.conj().T, 2e-8)
                self.assert_close(actual['expectations'], expected['expectations'], 2e-8)
                if 'channel' in actual:
                    representation = np.kron(unitary.conj(), unitary)
                    self.assert_close(actual['channel'], representation @ expected['channel'] @ representation.conj().T)

    def test_identity_choi(self):
        maximally_entangled = np.eye(3).ravel()
        self.assert_close(channel_to_choi(np.eye(9)), np.outer(maximally_entangled, maximally_entangled), 1e-14)

    def test_large_resonator_basis_covariance(self):
        from oqs.studies import oscillator, random_basis, rotate
        case = oscillator(112)
        basis = random_basis(112)
        expected = solve(case, OPTIONS)
        actual = solve(rotate(case, basis), OPTIONS)
        errors = np.linalg.norm(basis.conj().T @ actual['states'] @ basis - expected['states'], axis=(1, 2))
        self.assert_close(errors, np.zeros_like(errors), 1e-7)


if __name__ == '__main__':
    unittest.main()

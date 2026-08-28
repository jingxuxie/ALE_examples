"""Analytic, memory, and weak-noise checks for the private reference solver."""

import json
import unittest
from itertools import product

import numpy as np
from numpy.testing import assert_allclose
from scipy.linalg import expm

from reference_dynamics import solve_exact


PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z = np.diag([1.0, -1.0]).astype(complex)


def _law(kind, sigma=(0.7,), rates=(0.4,), mixing=((1.0,),)):
    return {"kind": kind, "mixing": mixing, "sigma": sigma, "rates": rates}


class ReferenceDynamicsTests(unittest.TestCase):
    def assert_channel(self, channel, diagnostics, expected, atol=2e-10):
        self.assertTrue(diagnostics["converged"], diagnostics)
        self.assertTrue(np.iscomplexobj(channel))
        assert_allclose(channel, expected, atol=atol, rtol=0)
        self.assertLess(diagnostics["trace_preservation_error"], 2e-11)
        self.assertLess(diagnostics["unitality_error"], 2e-11)
        self.assertLess(diagnostics["hermiticity_error"], 2e-11)
        self.assertGreater(diagnostics["choi_min_eigenvalue"], -2e-10)

    def test_commuting_gaussians(self):
        duration, sigma, rate, frequency = 1.3, 0.7, 0.4, 0.31
        for kind in ("static", "ou", "white"):
            with self.subTest(kind=kind):
                if kind == "static":
                    variance = sigma ** 2 * duration ** 2
                elif kind == "ou":
                    variance = 2 * sigma ** 2 * (rate * duration + np.expm1(-rate * duration)) / rate ** 2
                else:
                    variance = sigma ** 2 * duration
                decay = np.exp(-variance / 2)
                expected = np.diag([1, decay * np.exp(1j * frequency * duration), decay * np.exp(-1j * frequency * duration), 1])
                channel, diagnostics = solve_exact([duration], [frequency * PAULI_Z / 2], [[PAULI_Z / 2]], _law(kind))
                self.assert_channel(channel, diagnostics, expected)

    def test_telegraph_analytic_all_regimes(self):
        duration, sigma = 1.7, 0.7
        for rate in (0.0, 0.3, 0.7, 1.2):
            with self.subTest(rate=rate):
                root = np.sqrt(complex(rate ** 2 - sigma ** 2))
                factor = duration if abs(root) < 1e-14 else np.sinh(root * duration) / root
                decay = np.exp(-rate * duration) * (np.cosh(root * duration) + rate * factor)
                channel, diagnostics = solve_exact([duration], [0 * PAULI_Z], [[PAULI_Z / 2]], _law("telegraph", rates=[rate]))
                self.assert_channel(channel, diagnostics, np.diag([1, decay, decay, 1]), atol=5e-13)

    def test_mixing_and_sensitivity(self):
        mixing = np.array([[0.8, -0.2], [0.3, 1.1]])
        sigma = np.array([0.4, 0.6])
        coefficients = np.array([1.2, -0.7])
        duration = 1.4
        amplitudes = (coefficients @ mixing) * sigma
        for kind in ("static", "ou", "white"):
            with self.subTest(kind=kind):
                rates = np.array([0.3, 1.2])
                if kind == "static":
                    integrals = np.full(2, duration ** 2)
                elif kind == "ou":
                    integrals = 2 * (rates * duration + np.expm1(-rates * duration)) / rates ** 2
                else:
                    integrals = np.full(2, duration)
                decay = np.exp(-0.5 * np.dot(amplitudes ** 2, integrals))
                channel, diagnostics = solve_exact([duration], [0 * PAULI_Z], [[coefficient * PAULI_Z / 2 for coefficient in coefficients]], _law(kind, sigma, rates, mixing))
                self.assert_channel(channel, diagnostics, np.diag([1, decay, decay, 1]))

    def test_static_echo_retains_memory(self):
        channel, diagnostics = solve_exact([1.3, 1.3], [0 * PAULI_Z] * 2, [[PAULI_Z / 2], [-PAULI_Z / 2]], _law("static"))
        self.assert_channel(channel, diagnostics, np.eye(4), atol=2e-13)

    def test_ou_echo_retains_memory(self):
        duration, sigma, rate = 0.8, 0.7, 0.4
        individual = 2 * (rate * duration + np.expm1(-rate * duration)) / rate ** 2
        covariance = np.expm1(-rate * duration) ** 2 / rate ** 2
        decay = np.exp(-sigma ** 2 * (individual - covariance))
        channel, diagnostics = solve_exact([duration, duration], [0 * PAULI_Z] * 2, [[PAULI_Z / 2], [-PAULI_Z / 2]], _law("ou"))
        self.assert_channel(channel, diagnostics, np.diag([1, decay, decay, 1]))

    def test_noncommuting_split_invariance(self):
        durations = np.array([0.3, 0.7, 0.4])
        controls = np.array([0.4 * PAULI_X, 0.3 * PAULI_Y, -0.2 * PAULI_Z])
        operators = np.array([[PAULI_Z / 2, PAULI_Y / 3], [PAULI_X / 2, PAULI_Z / 3], [PAULI_Y / 2, PAULI_X / 3]])
        for kind in ("static", "ou", "telegraph", "white"):
            with self.subTest(kind=kind):
                law = _law(kind, [0.35, 0.2], [0.6, 1.1], [[1, -0.2], [0.4, 1]])
                channel, diagnostics = solve_exact(durations, controls, operators, law)
                split, split_diagnostics = solve_exact(np.repeat(durations / 2, 2), np.repeat(controls, 2, axis=0), np.repeat(operators, 2, axis=0), law)
                self.assert_channel(split, split_diagnostics, channel, atol=2e-13)
                self.assertTrue(diagnostics["converged"])

    def test_lab_frame_column_vectorization(self):
        for dimension in (2, 3, 6):
            with self.subTest(dimension=dimension):
                generator = np.random.default_rng(dimension)
                matrix = generator.normal(size=(dimension, dimension)) + 1j * generator.normal(size=(dimension, dimension))
                control = (matrix + matrix.conj().T) / 4
                unitary = expm(-0.37j * control)
                channel, diagnostics = solve_exact([0.37], [control], [[np.eye(dimension)]], _law("white"))
                self.assert_channel(channel, diagnostics, np.kron(unitary.conj(), unitary), atol=2e-14)
                density = matrix @ matrix.conj().T
                assert_allclose(channel @ density.reshape(-1, order="F"), (unitary @ density @ unitary.conj().T).reshape(-1, order="F"), atol=1e-12)

    def test_white_noncommuting_exact_generator(self):
        control = 0.7 * PAULI_Y
        operators = [0.2 * PAULI_Z, 0.3 * PAULI_X]
        mixing = np.array([[1, 0.3], [-0.2, 0.8]])
        sigma = np.array([0.5, 0.9])
        identity = np.eye(2)
        control_ad = np.kron(identity, control) - np.kron(control.T, identity)
        generator = -1j * control_ad
        for latent in range(2):
            loaded = sum(mixing[channel, latent] * operators[channel] for channel in range(2)) * sigma[latent]
            noise_ad = np.kron(identity, loaded) - np.kron(loaded.T, identity)
            generator -= noise_ad @ noise_ad / 2
        channel, diagnostics = solve_exact([1.2], [control], [operators], _law("white", sigma, [1, 1], mixing))
        self.assert_channel(channel, diagnostics, expm(1.2 * generator), atol=2e-13)

    def test_zero_rate_ou_is_static(self):
        arguments = ([1.4], [0.6 * PAULI_Y], [[PAULI_Z / 2]])
        static, _ = solve_exact(*arguments, _law("static"))
        ou, diagnostics = solve_exact(*arguments, _law("ou", rates=[0]))
        self.assert_channel(ou, diagnostics, static, atol=1e-14)

    def test_weak_noise_corrections(self):
        duration, sigma, frequency = 1.3, 0.0007, 0.31
        for kind in ("static", "ou", "telegraph", "white"):
            with self.subTest(kind=kind):
                rate = 0.4 if kind == "ou" else 0.0
                law = _law(kind, sigma=[sigma], rates=[rate])
                law["return_noise_correction"] = True
                channel, diagnostics = solve_exact([duration], [frequency * PAULI_Z / 2], [[PAULI_Z / 2]], law)
                if kind == "telegraph":
                    delta = -2 * np.sin(sigma * duration / 2) ** 2
                else:
                    if kind == "white":
                        variance = duration
                    elif kind == "ou":
                        variance = 2 * (rate * duration + np.expm1(-rate * duration)) / rate ** 2
                    else:
                        variance = duration ** 2
                    delta = np.expm1(-0.5 * sigma ** 2 * variance)
                expected = np.diag([0, delta * np.exp(1j * frequency * duration), delta * np.exp(-1j * frequency * duration), 0])
                assert_allclose(diagnostics["noise_correction"], expected, atol=5e-19, rtol=2e-11)
                self.assertTrue(diagnostics["converged"])
                self.assertTrue(np.iscomplexobj(channel))

    def test_many_latent_weak_ou_converges_at_degree_three(self):
        for latent_count in (7, 9):
            with self.subTest(latent_count=latent_count):
                sigma = np.linspace(2e-5, 4e-5, latent_count)
                rates = np.linspace(0.2, 4.0, latent_count)
                duration = 1.1
                law = _law("ou", sigma, rates, np.ones((1, latent_count)))
                channel, diagnostics = solve_exact([duration], [0.2 * PAULI_Y], [[PAULI_Z / 2]], law)
                self.assertTrue(diagnostics["converged"], diagnostics)
                self.assertEqual([entry["order"] for entry in diagnostics["history"]], [1, 2, 3])
                json.dumps(diagnostics, allow_nan=False)
                commuting, commuting_diagnostics = solve_exact([duration], [0 * PAULI_Y], [[PAULI_Z / 2]], law)
                variance = np.sum(2 * sigma ** 2 * (rates * duration + np.expm1(-rates * duration)) / rates ** 2)
                decay = np.exp(-variance / 2)
                self.assert_channel(commuting, commuting_diagnostics, np.diag([1, decay, decay, 1]), atol=1e-14)

    def test_private_ou_refinement_override(self):
        law = _law("ou", sigma=[0.01])
        law["hierarchy_degrees"] = [1, 2]
        channel, diagnostics = solve_exact([0.7], [PAULI_Y], [[PAULI_Z / 2]], law)
        self.assertFalse(diagnostics["converged"])
        self.assertEqual([entry["order"] for entry in diagnostics["history"]], [1, 2])
        self.assertEqual(channel.shape, (4, 4))
        for invalid in ([], [2, 1], [1, 1], [1, 2.5], [0, 1]):
            law["hierarchy_degrees"] = invalid
            with self.assertRaises(ValueError):
                solve_exact([0.7], [PAULI_Y], [[PAULI_Z / 2]], law)

    def test_telegraph_physical_finite_states(self):
        random = np.random.default_rng(62)
        dimension, latent_count = 3, 2
        matrices = random.normal(size=(2, 3, dimension, dimension)) + 1j * random.normal(size=(2, 3, dimension, dimension))
        matrices = (matrices + matrices.swapaxes(-1, -2).conj()) / 4
        durations = [0.3, 0.6]
        controls, operators = matrices[:, 0], matrices[:, 1:]
        sigma = np.array([0.5, 0.3])
        rates = np.array([0.4, 0.9])
        mixing = np.array([[0.7, -0.2], [0.3, 1.1]])
        signs = list(product((-1, 1), repeat=latent_count))
        channel_size = dimension ** 2
        state = np.tile(np.eye(channel_size), (len(signs), 1)).astype(complex) / len(signs)
        identity = np.eye(dimension)
        for duration, control, noise in zip(durations, controls, operators):
            generator = np.zeros((len(signs) * channel_size,) * 2, dtype=complex)
            for index, sign in enumerate(signs):
                block = slice(index * channel_size, (index + 1) * channel_size)
                physical = mixing @ (sigma * sign)
                hamiltonian = control + np.einsum("a,aij->ij", physical, noise)
                generator[block, block] = -1j * (np.kron(identity, hamiltonian) - np.kron(hamiltonian.T, identity)) - sum(rates) * np.eye(channel_size)
                for latent in range(latent_count):
                    neighbor = list(sign)
                    neighbor[latent] *= -1
                    column = signs.index(tuple(neighbor))
                    generator[block, column * channel_size:(column + 1) * channel_size] += rates[latent] * np.eye(channel_size)
            state = expm(duration * generator) @ state
        expected = state.reshape(len(signs), channel_size, channel_size).sum(axis=0)
        channel, diagnostics = solve_exact(durations, controls, operators, _law("telegraph", sigma, rates, mixing))
        self.assert_channel(channel, diagnostics, expected, atol=2e-13)

    def test_tiny_amplitude_second_cumulant_extrapolation(self):
        duration, sigma, rate = 1.7, 0.6, 0.4
        for kind in ("static", "ou", "telegraph", "white"):
            with self.subTest(kind=kind):
                scaled_corrections = []
                for factor in (0.002, 0.001):
                    law = _law(kind, sigma=[sigma * factor], rates=[rate])
                    law["return_noise_correction"] = True
                    _, diagnostics = solve_exact([duration], [0.3 * PAULI_Z], [[PAULI_Z / 2]], law)
                    self.assertTrue(diagnostics["converged"])
                    scaled_corrections.append(diagnostics["noise_correction"] / factor ** 2)
                extrapolated = (4 * scaled_corrections[1] - scaled_corrections[0]) / 3
                if kind == "static":
                    variance = sigma ** 2 * duration ** 2
                elif kind == "white":
                    variance = sigma ** 2 * duration
                else:
                    decay_rate = rate * (2 if kind == "telegraph" else 1)
                    variance = 2 * sigma ** 2 * (decay_rate * duration + np.expm1(-decay_rate * duration)) / decay_rate ** 2
                expected = np.diag([0, -variance / 2 * np.exp(0.6j * duration), -variance / 2 * np.exp(-0.6j * duration), 0])
                assert_allclose(extrapolated, expected, atol=2e-12, rtol=0)

    def test_deterministic_and_json_safe(self):
        for kind in ("static", "ou", "telegraph", "white"):
            with self.subTest(kind=kind):
                state_before = np.random.get_state()
                arguments = ([0.6], [0.7 * PAULI_Y], [[PAULI_Z / 2]], _law(kind))
                first, diagnostics = solve_exact(*arguments)
                second, _ = solve_exact(*arguments)
                self.assertTrue(np.array_equal(first, second))
                state_after = np.random.get_state()
                self.assertEqual(state_before[0], state_after[0])
                self.assertTrue(np.array_equal(state_before[1], state_after[1]))
                self.assertEqual(state_before[2:], state_after[2:])
                json.dumps(diagnostics, allow_nan=False)

    def test_empty_sequence_and_zero_sigma(self):
        empty, diagnostics = solve_exact([], np.empty((0, 3, 3)), np.empty((0, 1, 3, 3)), _law("ou"))
        self.assert_channel(empty, diagnostics, np.eye(9), atol=0)
        for kind in ("static", "ou", "telegraph", "white"):
            channel, diagnostics = solve_exact([0, 0.5], [PAULI_X, PAULI_Y], [[PAULI_Z], [PAULI_Z]], _law(kind, sigma=[0]))
            unitary = expm(-0.5j * PAULI_Y)
            self.assert_channel(channel, diagnostics, np.kron(unitary.conj(), unitary), atol=1e-14)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            solve_exact([-1], [PAULI_X], [[PAULI_Z]], _law("static"))
        with self.assertRaises(ValueError):
            solve_exact([1], [PAULI_X + 1j * PAULI_Y], [[PAULI_Z]], _law("ou"))
        with self.assertRaises(ValueError):
            solve_exact([1], [PAULI_X], [[PAULI_Z]], _law("telegraph", rates=[-1]))
        with self.assertRaises(ValueError):
            solve_exact([1], [PAULI_X], [[PAULI_Z]], _law("white"), tolerance=0)


if __name__ == "__main__":
    unittest.main()

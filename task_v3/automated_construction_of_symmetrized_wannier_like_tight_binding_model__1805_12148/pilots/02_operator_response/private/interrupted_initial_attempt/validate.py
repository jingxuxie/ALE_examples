"""Independent finite-difference, gauge, frame, and group-projection checks."""

import unittest

import numpy as np

from operators import project_operators
from response import FourierModel, hermitian, point_response, responses


def example_model(orbital_count=4):
    generator = np.random.default_rng(813)
    vectors = np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0],
                        [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])
    hopping = 0.08 * (generator.normal(size=(7, orbital_count, orbital_count))
                      + 1j * generator.normal(size=(7, orbital_count, orbital_count)))
    hopping[0] = hermitian(hopping[0]) + np.diag(np.linspace(-3, 3, orbital_count))
    for source, partner in ((1, 2), (3, 4), (5, 6)):
        hopping[partner] = hopping[source].conj().T
    connection = 0.1 * (generator.normal(size=(7, orbital_count, orbital_count, 3))
                        + 1j * generator.normal(size=(7, orbital_count, orbital_count, 3)))
    connection[0] = hermitian(connection[0].transpose(2, 0, 1)).transpose(1, 2, 0)
    diagonal = np.arange(orbital_count)
    connection[0, diagonal, diagonal] = 0
    return {
        "lattice": np.array([[2.1, 0.3, -0.1], [0.2, 1.7, 0.4], [0.05, -0.2, 2.5]]),
        "rvec": vectors,
        "ham": hopping,
        "connection": connection,
        "centers": 0.2 * generator.normal(size=(orbital_count, 3)),
        "fractional_rotations": np.eye(3, dtype=int)[None],
        "cartesian_rotations": np.eye(3)[None],
        "translations": np.zeros((1, 3)),
        "antiunitary": np.array([False]),
        "unitary": np.eye(orbital_count, dtype=complex)[None],
        "orbital_shifts": np.zeros((1, orbital_count, 3), dtype=int),
        "query_points": np.array([[0.13, -0.27, 0.08], [-0.13, 0.27, -0.08]]),
    }


def change_orbitals(payload, basis):
    orbital_count = len(basis)
    diagonal = np.arange(orbital_count)
    position = payload["connection"].transpose(3, 0, 1, 2).copy()
    origin = np.flatnonzero(np.all(payload["rvec"] == 0, axis=1))[0]
    position[:, origin, diagonal, diagonal] += payload["centers"].T
    position = basis.conj().T @ position @ basis
    centers = position[:, origin, diagonal, diagonal].real.T.copy()
    position[:, origin, diagonal, diagonal] -= centers.T
    return dict(payload, ham=basis.conj().T @ payload["ham"] @ basis,
                connection=position.transpose(1, 2, 3, 0), centers=centers)


def finite_difference_response(payload, point, occupied, step=2e-5):
    model = FourierModel(payload)
    hopping, _, connection, _ = model.at(point)
    _, eigenvectors = np.linalg.eigh(hopping)
    filled = eigenvectors[:, :occupied]
    projector = filled @ filled.conj().T
    complement = np.eye(len(hopping)) - projector
    projector_derivatives = []
    connection_derivatives = []
    for axis in range(3):
        displacement = step * payload["lattice"][:, axis] / (2 * np.pi)
        plus_hopping, _, plus_connection, _ = model.at(point + displacement)
        minus_hopping, _, minus_connection, _ = model.at(point - displacement)
        _, plus_vectors = np.linalg.eigh(plus_hopping)
        _, minus_vectors = np.linalg.eigh(minus_hopping)
        plus_projector = plus_vectors[:, :occupied] @ plus_vectors[:, :occupied].conj().T
        minus_projector = minus_vectors[:, :occupied] @ minus_vectors[:, :occupied].conj().T
        projector_derivatives.append((plus_projector - minus_projector) / (2 * step))
        connection_derivatives.append((plus_connection - minus_connection) / (2 * step))
    berry = []
    for first, second in ((1, 2), (2, 0), (0, 1)):
        derivative_first = projector_derivatives[first]
        derivative_second = projector_derivatives[second]
        commutator = derivative_first @ derivative_second - derivative_second @ derivative_first
        curl = connection_derivatives[first][second] - connection_derivatives[second][first]
        curvature = (1j * np.trace(projector @ commutator)
                     + np.trace(derivative_first @ connection[second] - derivative_second @ connection[first])
                     + np.trace(projector @ curl))
        berry.append(curvature.real)
    optical = np.empty((3, 3), dtype=complex)
    for first in range(3):
        for second in range(3):
            optical[first, second] = 1j * np.trace(
                projector @ (connection[first] - 1j * projector_derivatives[first])
                @ complement @ (connection[second] + 1j * projector_derivatives[second])
            )
    return np.array(berry), optical


class ScientificChecks(unittest.TestCase):
    def assert_models_equal(self, first, second, tolerance=2e-12):
        np.testing.assert_allclose(first["centers"], second["centers"], atol=tolerance, rtol=0)
        for name in ("ham", "connection"):
            left = {tuple(vector): value for vector, value in zip(first["rvec"], first[name])}
            right = {tuple(vector): value for vector, value in zip(second["rvec"], second[name])}
            for vector in left.keys() | right.keys():
                np.testing.assert_allclose(left.get(vector, 0), right.get(vector, 0), atol=tolerance, rtol=0)

    def test_identity_preserves_nonhermitian_coefficients(self):
        payload = example_model()
        self.assert_models_equal(payload, project_operators(payload))

    def test_cartesian_fourier_derivatives(self):
        payload = example_model()
        model = FourierModel(payload)
        point = payload["query_points"][0]
        _, hopping_derivative, _, connection_derivative = model.at(point)
        step = 1e-5
        for axis in range(3):
            displacement = step * payload["lattice"][:, axis] / (2 * np.pi)
            plus = model.at(point + displacement)
            minus = model.at(point - displacement)
            np.testing.assert_allclose(hopping_derivative[axis], (plus[0] - minus[0]) / (2 * step), atol=1e-9, rtol=1e-8)
            np.testing.assert_allclose(connection_derivative[axis], (plus[2] - minus[2]) / (2 * step), atol=1e-9, rtol=1e-8)

    def test_response_against_projector_finite_differences(self):
        payload = example_model()
        _, berry, optical = responses(payload, 2)
        for index, point in enumerate(payload["query_points"]):
            reference_berry, reference_optical = finite_difference_response(payload, point, 2)
            np.testing.assert_allclose(berry[index], reference_berry, atol=3e-9, rtol=2e-8)
            np.testing.assert_allclose(optical[index], reference_optical, atol=3e-9, rtol=2e-8)
        np.testing.assert_allclose(optical + optical.swapaxes(1, 2).conj(), 0, atol=1e-14)
        self.assertGreaterEqual(np.linalg.eigvalsh(-1j * optical).min(), -1e-14)

    def test_analytic_two_band_sign(self):
        pauli = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]])
        point = np.array([0.31, -0.62])
        direction = np.array([np.sin(point[0]), np.sin(point[1]), 0.6 + np.cos(point[0]) + np.cos(point[1])])
        first_derivative = np.array([np.cos(point[0]), 0, -np.sin(point[0])])
        second_derivative = np.array([0, np.cos(point[1]), -np.sin(point[1])])
        hopping = np.einsum("a,anm->nm", direction, pauli)
        derivative = np.einsum("ba,anm->bnm", np.array([first_derivative, second_derivative, np.zeros(3)]), pauli)
        _, berry, _ = point_response(hopping, derivative, np.zeros((3, 2, 2)), np.zeros((3, 3, 2, 2)), 1)
        expected = np.dot(direction, np.cross(first_derivative, second_derivative)) / (2 * np.linalg.norm(direction) ** 3)
        np.testing.assert_allclose(berry, [0, 0, expected], atol=1e-14)

    def test_connection_only_is_not_velocity_only(self):
        hopping = np.diag([-1.0, 1.0])
        connection = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], np.zeros((2, 2))])
        _, berry, optical = point_response(hopping, np.zeros((3, 2, 2)), connection, np.zeros((3, 3, 2, 2)), 1)
        np.testing.assert_allclose(berry, 0, atol=1e-14)
        self.assertAlmostEqual(optical[0, 0].imag, 1)
        self.assertAlmostEqual(optical[0, 1].real, -1)

    def test_empty_and_complete_subspaces(self):
        payload = example_model()
        _, empty_berry, empty_optical = responses(payload, 0)
        np.testing.assert_array_equal(empty_berry, 0)
        np.testing.assert_array_equal(empty_optical, 0)
        _, full_berry, full_optical = responses(payload, 4)
        np.testing.assert_array_equal(full_optical, 0)
        model = FourierModel(payload)
        for index, point in enumerate(payload["query_points"]):
            derivative = model.at(point)[3]
            expected = [np.trace(derivative[first, second] - derivative[second, first]).real
                        for first, second in ((1, 2), (2, 0), (0, 1))]
            np.testing.assert_allclose(full_berry[index], expected, atol=1e-14)

    def test_dense_orbital_basis_gauge_invariance(self):
        payload = example_model()
        generator = np.random.default_rng(182)
        basis, _ = np.linalg.qr(generator.normal(size=(4, 4)) + 1j * generator.normal(size=(4, 4)))
        transformed = change_orbitals(payload, basis)
        for original, changed in zip(responses(payload, 2), responses(transformed, 2)):
            np.testing.assert_allclose(original, changed, atol=3e-13, rtol=3e-13)

    def test_degenerate_included_subspaces(self):
        payload = example_model()
        payload["ham"][:] = 0
        payload["ham"][0] = np.diag([-2, -2, 2, 2])
        generator = np.random.default_rng(932)
        basis, _ = np.linalg.qr(generator.normal(size=(4, 4)) + 1j * generator.normal(size=(4, 4)))
        transformed = change_orbitals(payload, basis)
        for original, changed in zip(responses(payload, 2), responses(transformed, 2)):
            np.testing.assert_allclose(original, changed, atol=2e-13, rtol=2e-13)

    def test_improper_passive_cartesian_frame(self):
        payload = example_model()
        generator = np.random.default_rng(813)
        frame, _ = np.linalg.qr(generator.normal(size=(3, 3)))
        frame[:, 0] *= -np.linalg.det(frame)
        transformed = dict(payload,
                           lattice=payload["lattice"] @ frame.T,
                           centers=payload["centers"] @ frame.T,
                           connection=np.einsum("ab,rnmb->rnma", frame, payload["connection"]))
        energies, berry, optical = responses(payload, 2)
        new_energies, new_berry, new_optical = responses(transformed, 2)
        np.testing.assert_allclose(new_energies, energies, atol=1e-13)
        np.testing.assert_allclose(new_berry, np.linalg.det(frame) * berry @ frame.T, atol=1e-13)
        np.testing.assert_allclose(new_optical, frame @ optical @ frame.T, atol=1e-13)

    def test_dense_affine_inversion_projection(self):
        payload = example_model()
        generator = np.random.default_rng(914)
        basis, _ = np.linalg.qr(generator.normal(size=(4, 4)) + 1j * generator.normal(size=(4, 4)))
        inversion = basis @ np.diag([1, 1, -1, -1]) @ basis.conj().T
        payload.update(
            fractional_rotations=np.array([np.eye(3, dtype=int), -np.eye(3, dtype=int)]),
            cartesian_rotations=np.array([np.eye(3), -np.eye(3)]),
            translations=np.array([[0, 0, 0], [0.3, -0.2, 0.1]]),
            antiunitary=np.array([False, False]),
            unitary=np.array([np.eye(4), inversion]),
            orbital_shifts=np.zeros((2, 4, 3), dtype=int),
        )
        repaired = project_operators(payload)
        self.assert_models_equal(repaired, project_operators(dict(payload, **repaired)))
        _, berry, optical = responses(dict(payload, **repaired), 2)
        np.testing.assert_allclose(berry[0], berry[1], atol=2e-12)
        np.testing.assert_allclose(optical[0], optical[1], atol=2e-12)

    def test_nonsymmorphic_support_and_affine_shift(self):
        payload = example_model(2)
        payload.update(
            lattice=np.diag([2.0, 3.0, 4.0]),
            fractional_rotations=np.array([np.eye(3, dtype=int), np.diag([-1, -1, 1])]),
            cartesian_rotations=np.array([np.eye(3), np.diag([-1, -1, 1])]),
            translations=np.array([[0, 0, 0], [0, 0, 0.5]]),
            antiunitary=np.array([False, False]),
            unitary=np.array([np.eye(2), [[0, 1], [1, 0]]], dtype=complex),
            orbital_shifts=np.array([[[0, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 0, 1]]]),
        )
        repaired = project_operators(payload)
        self.assert_models_equal(repaired, project_operators(dict(payload, **repaired)))
        self.assertGreater(len(repaired["rvec"]), len(payload["rvec"]))
        self.assertAlmostEqual(repaired["centers"][1, 2] - repaired["centers"][0, 2], 2)

    def test_antiunitary_time_reversal(self):
        payload = example_model(2)
        payload.update(
            fractional_rotations=np.array([np.eye(3, dtype=int)] * 2),
            cartesian_rotations=np.array([np.eye(3)] * 2),
            translations=np.zeros((2, 3)),
            antiunitary=np.array([False, True]),
            unitary=np.array([np.eye(2), [[0, 1], [-1, 0]]], dtype=complex),
            orbital_shifts=np.zeros((2, 2, 3), dtype=int),
        )
        repaired = project_operators(payload)
        self.assert_models_equal(repaired, project_operators(dict(payload, **repaired)))
        _, berry, optical = responses(dict(payload, **repaired), 1)
        np.testing.assert_allclose(berry[0], -berry[1], atol=2e-11)
        np.testing.assert_allclose(optical[0], -optical[1].conj(), atol=2e-11)


if __name__ == "__main__":
    unittest.main(verbosity=2)

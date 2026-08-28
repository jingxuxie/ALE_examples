"""Independent finite-difference, covariance, and real-space projection checks."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
from numpy.testing import assert_allclose

from response import FourierModel, hermitian_part, point_response, responses
from symmetry import project_operators


def random_complex(generator, shape):
    return generator.normal(size=shape) + 1j * generator.normal(size=shape)


def sample_model():
    generator = np.random.default_rng(1984)
    orbital_count = 4
    vectors = np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]])
    hopping = 0.1 * random_complex(generator, (len(vectors), orbital_count, orbital_count))
    hopping[0] = hermitian_part(hopping[0]) + np.diag([-3, -2, 2, 4])
    hopping[2] = hopping[1].conj().T
    hopping[4] = hopping[3].conj().T
    connection = 0.1 * random_complex(generator, hopping.shape + (3,))
    connection[0, np.arange(orbital_count), np.arange(orbital_count)] = 0
    orbital_rotation = np.array([
        [np.cos(0.6), np.sin(0.6) * np.exp(0.3j)],
        [np.sin(0.6) * np.exp(-0.3j), -np.cos(0.6)],
    ])
    screw = np.kron(np.array([[0, 1], [1, 0]]), orbital_rotation)
    rotation = np.diag([-1, -1, 1])
    return {
        "lattice": np.diag([2.0, 3.0, 4.0]),
        "rvec": vectors,
        "ham": hopping,
        "connection": connection,
        "centers": generator.normal(size=(orbital_count, 3)),
        "query_points": np.array([[0.137, -0.223, 0.092]]),
        "fractional_rotations": np.array([np.eye(3, dtype=int), rotation]),
        "cartesian_rotations": np.array([np.eye(3), rotation]),
        "translations": np.array([[0, 0, 0], [0, 0, 0.5]]),
        "antiunitary": np.array([False, False]),
        "unitary": np.array([np.eye(orbital_count), screw]),
        "orbital_shifts": np.array([
            np.zeros((orbital_count, 3), dtype=int),
            [[0, 0, 0], [0, 0, 0], [0, 0, 1], [0, 0, 1]],
        ]),
    }


def full_position(payload):
    position = payload["connection"].copy()
    zero = np.flatnonzero(np.all(payload["rvec"] == 0, axis=1))[0]
    diagonal = np.arange(len(payload["centers"]))
    position[zero, diagonal, diagonal] += payload["centers"]
    return position


def compare_coefficients(first, second, name, tolerance=1e-11):
    first_values = {tuple(vector): value for vector, value in zip(first["rvec"], first[name])}
    second_values = {tuple(vector): value for vector, value in zip(second["rvec"], second[name])}
    for vector in first_values.keys() | second_values.keys():
        assert_allclose(first_values.get(vector, 0), second_values.get(vector, 0), atol=tolerance, rtol=tolerance)


def brute_projection(payload):
    orbital_count = len(payload["centers"])
    position = full_position(payload)
    hopping_result = {}
    position_result = {}
    operation_count = len(payload["unitary"])
    for operation in range(operation_count):
        unitary = payload["unitary"][operation]
        rotation = payload["fractional_rotations"][operation]
        cartesian = payload["cartesian_rotations"][operation]
        shifts = payload["orbital_shifts"][operation]
        for row, vector in enumerate(payload["rvec"]):
            for source_left in range(orbital_count):
                for source_right in range(orbital_count):
                    target_vector = tuple(rotation @ vector + shifts[source_right] - shifts[source_left])
                    if target_vector not in hopping_result:
                        hopping_result[target_vector] = np.zeros((orbital_count, orbital_count), complex)
                        position_result[target_vector] = np.zeros((orbital_count, orbital_count, 3), complex)
                    hopping = payload["ham"][row, source_left, source_right]
                    matrix_element = position[row, source_left, source_right]
                    if payload["antiunitary"][operation]:
                        hopping = hopping.conjugate()
                        matrix_element = matrix_element.conjugate()
                    transformed_position = cartesian @ matrix_element
                    if not np.any(vector) and source_left == source_right:
                        transformed_position += (payload["translations"][operation] - shifts[source_left]) @ payload["lattice"]
                    for target_left in range(orbital_count):
                        for target_right in range(orbital_count):
                            weight = unitary[target_left, source_left] * unitary[target_right, source_right].conjugate() / operation_count
                            hopping_result[target_vector][target_left, target_right] += weight * hopping
                            position_result[target_vector][target_left, target_right] += weight * transformed_position
    vectors = np.array(sorted(hopping_result))
    return {
        "rvec": vectors,
        "ham": np.array([hopping_result[tuple(vector)] for vector in vectors]),
        "position": np.array([position_result[tuple(vector)] for vector in vectors]),
    }


def finite_difference_berry(payload, occupied, step):
    model = FourierModel(payload)
    point = payload["query_points"][0]
    hamiltonian = model.evaluate(point)[0]
    eigenvectors = np.linalg.eigh(hamiltonian)[1][:, :occupied]
    projector = eigenvectors @ eigenvectors.conj().T
    projector_derivatives = []
    connection_trace_derivatives = []
    for direction in range(3):
        displacement = step * payload["lattice"][:, direction] / (2 * np.pi)
        projectors = []
        traces = []
        for sign in [1, -1]:
            hamiltonian, connection, _, _ = model.evaluate(point + sign * displacement)
            eigenvectors = np.linalg.eigh(hamiltonian)[1][:, :occupied]
            shifted_projector = eigenvectors @ eigenvectors.conj().T
            projectors.append(shifted_projector)
            traces.append(np.einsum("nm,amn->a", shifted_projector, connection).real)
        projector_derivatives.append((projectors[0] - projectors[1]) / (2 * step))
        connection_trace_derivatives.append((traces[0] - traces[1]) / (2 * step))
    curvature = []
    for first, second in [(1, 2), (2, 0), (0, 1)]:
        commutator = (
            projector_derivatives[first] @ projector_derivatives[second]
            - projector_derivatives[second] @ projector_derivatives[first]
        )
        curvature.append(
            (1j * np.trace(projector @ commutator)).real
            + connection_trace_derivatives[first][second]
            - connection_trace_derivatives[second][first]
        )
    return np.array(curvature)


class SolverTests(unittest.TestCase):
    def test_brute_affine_projection(self):
        payload = sample_model()
        repaired = project_operators(payload)
        brute = brute_projection(payload)
        compare_coefficients(repaired, brute, "ham")
        repaired["position"] = full_position(repaired)
        compare_coefficients(repaired, brute, "position")
        self.assertGreater(len(repaired["rvec"]), len(payload["rvec"]))

    def test_projection_idempotence(self):
        payload = sample_model()
        first = project_operators(payload)
        second = project_operators(dict(payload, **first))
        compare_coefficients(first, second, "ham")
        compare_coefficients(first, second, "connection")
        assert_allclose(first["centers"], second["centers"], atol=2e-14)

    def test_identity_preserves_nonhermitian_coefficients(self):
        payload = sample_model()
        for name in ["unitary", "fractional_rotations", "cartesian_rotations", "orbital_shifts", "translations", "antiunitary"]:
            payload[name] = payload[name][:1]
        repaired = project_operators(payload)
        compare_coefficients(payload, repaired, "ham")
        compare_coefficients(payload, repaired, "connection")
        assert_allclose(payload["centers"], repaired["centers"], atol=1e-14)

    def test_fourier_derivatives_and_curvature(self):
        payload = sample_model()
        payload["lattice"] = np.array([[2.1, 0.2, -0.3], [0.4, 2.7, 0.1], [0.1, 0.3, 3.5]])
        model = FourierModel(payload)
        point = payload["query_points"][0]
        _, _, hamiltonian_derivative, connection_derivative = model.evaluate(point)
        step = 1e-5
        for direction in range(3):
            displacement = step * payload["lattice"][:, direction] / (2 * np.pi)
            forward = model.evaluate(point + displacement)
            backward = model.evaluate(point - displacement)
            assert_allclose((forward[0] - backward[0]) / (2 * step), hamiltonian_derivative[direction], atol=2e-8)
            assert_allclose((forward[1] - backward[1]) / (2 * step), connection_derivative[direction], atol=2e-8)
        _, berry, optical = responses(payload, 2)
        assert_allclose(finite_difference_berry(payload, 2, step), berry[0], atol=2e-8)
        assert_allclose(optical + optical.conj().transpose(0, 2, 1), 0, atol=1e-14)
        self.assertGreaterEqual(np.min(np.linalg.eigvalsh(optical / 1j)), -1e-14)

    def test_center_embedding_gauge(self):
        payload = sample_model()
        shifted = dict(payload)
        displacement = np.random.default_rng(7).normal(size=payload["centers"].shape)
        shifted["centers"] = payload["centers"] + displacement
        shifted["connection"] = payload["connection"].copy()
        shifted["connection"][0, np.arange(4), np.arange(4)] -= displacement
        for original, regauged in zip(responses(payload, 2), responses(shifted, 2)):
            assert_allclose(original, regauged, atol=2e-13)

    def test_optical_against_projector_finite_differences(self):
        payload = sample_model()
        model = FourierModel(payload)
        point = payload["query_points"][0]
        hamiltonian, connection, _, _ = model.evaluate(point)
        eigenvectors = np.linalg.eigh(hamiltonian)[1]
        step = 1e-5
        transitions = []
        for direction in range(3):
            displacement = step * payload["lattice"][:, direction] / (2 * np.pi)
            projectors = []
            for sign in [1, -1]:
                shifted_hamiltonian = model.evaluate(point + sign * displacement)[0]
                occupied_vectors = np.linalg.eigh(shifted_hamiltonian)[1][:, :2]
                projectors.append(occupied_vectors @ occupied_vectors.conj().T)
            projector_derivative = (projectors[0] - projectors[1]) / (2 * step)
            transitions.append(
                (eigenvectors.conj().T @ (connection[direction] - 1j * projector_derivative) @ eigenvectors)[:2, 2:]
            )
        transitions = np.array(transitions)
        expected = 1j * np.einsum("anm,bnm->ab", transitions, transitions.conj())
        assert_allclose(responses(payload, 2)[2][0], expected, atol=2e-9)

    def test_two_band_curvature_sign(self):
        pauli = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]])
        field = np.array([0.3, 0.5, 0.7])
        derivatives = np.array([[0.4, -0.2, 0.1], [0.3, 0.6, -0.1], [-0.2, 0.1, 0.2]])
        hamiltonian = np.einsum("a,anm->nm", field, pauli)
        gradient = np.einsum("ab,bnm->anm", derivatives, pauli)
        _, berry, optical = point_response(
            hamiltonian, np.zeros((3, 2, 2), complex), gradient, np.zeros((3, 3, 2, 2), complex), 1
        )
        expected = np.array([
            np.dot(field, np.cross(derivatives[first], derivatives[second])) / (2 * np.linalg.norm(field)**3)
            for first, second in [(1, 2), (2, 0), (0, 1)]
        ])
        assert_allclose(berry, expected, atol=1e-14)
        assert_allclose(berry, 2 * optical.real[[1, 2, 0], [2, 0, 1]], atol=1e-14)

    def test_orbital_permutation(self):
        payload = sample_model()
        order = np.array([2, 0, 3, 1])
        reordered = dict(payload)
        reordered["centers"] = payload["centers"][order]
        reordered["orbital_shifts"] = payload["orbital_shifts"][:, order]
        for name in ["ham", "connection", "unitary"]:
            reordered[name] = payload[name][:, order][:, :, order]
        original = project_operators(payload)
        permuted = project_operators(reordered)
        assert_allclose(original["rvec"], permuted["rvec"])
        assert_allclose(original["centers"][order], permuted["centers"], atol=1e-14)
        for name in ["ham", "connection"]:
            assert_allclose(original[name][:, order][:, :, order], permuted[name], atol=1e-14)
        for native, changed in zip(responses(payload, 2), responses(reordered, 2)):
            assert_allclose(native, changed, atol=2e-13)

    def test_complex_local_orbital_basis(self):
        payload = sample_model()
        generator = np.random.default_rng(23)
        basis = np.zeros((4, 4), complex)
        basis[:2, :2] = np.linalg.qr(random_complex(generator, (2, 2)))[0]
        basis[2:, 2:] = np.linalg.qr(random_complex(generator, (2, 2)))[0]
        adjoint = basis.conj().T
        rotated = dict(payload)
        rotated["ham"] = adjoint @ payload["ham"] @ basis
        rotated["unitary"] = adjoint @ payload["unitary"] @ basis
        position = np.moveaxis(adjoint @ np.moveaxis(full_position(payload), -1, 1) @ basis, 1, -1)
        centers = position[0, np.arange(4), np.arange(4)].real.copy()
        position[0, np.arange(4), np.arange(4)] -= centers
        rotated["centers"] = centers
        rotated["connection"] = position
        native_repaired = project_operators(payload)
        rotated_repaired = project_operators(rotated)
        expected = np.moveaxis(adjoint @ np.moveaxis(full_position(native_repaired), -1, 1) @ basis, 1, -1)
        assert_allclose(expected, full_position(rotated_repaired), atol=3e-14)
        assert_allclose(adjoint @ native_repaired["ham"] @ basis, rotated_repaired["ham"], atol=3e-14)
        for native, changed in [(payload, rotated), (dict(payload, **native_repaired), dict(rotated, **rotated_repaired))]:
            for original, transformed in zip(responses(native, 2), responses(changed, 2)):
                assert_allclose(original, transformed, atol=3e-13)

    def test_spinful_time_reversal(self):
        payload = sample_model()
        time_reversal = np.kron(np.eye(2), np.array([[0, 1], [-1, 0]]))
        payload["unitary"] = np.array([np.eye(4), time_reversal])
        payload["antiunitary"] = np.array([False, True])
        payload["fractional_rotations"] = np.array([np.eye(3, dtype=int)] * 2)
        payload["cartesian_rotations"] = np.array([np.eye(3)] * 2)
        payload["orbital_shifts"] = np.zeros((2, 4, 3), dtype=int)
        payload["translations"] = np.zeros((2, 3))
        payload["query_points"] = np.concatenate((payload["query_points"], -payload["query_points"]))
        repaired = project_operators(payload)
        brute = brute_projection(payload)
        compare_coefficients(repaired, brute, "ham")
        compare_coefficients(dict(repaired, position=full_position(repaired)), brute, "position")
        energies, berry, optical = responses(dict(payload, **repaired), 2)
        assert_allclose(energies[0], energies[1], atol=2e-14)
        assert_allclose(berry[0], -berry[1], atol=2e-13)
        assert_allclose(optical[0], -optical[1].conj(), atol=2e-13)

    def test_improper_frame_covariance(self):
        payload = sample_model()
        frame = np.linalg.qr(np.random.default_rng(31).normal(size=(3, 3)))[0]
        frame[:, 0] *= -np.linalg.det(frame)
        displayed = dict(payload)
        for name in ["lattice", "centers", "connection"]:
            displayed[name] = payload[name] @ frame.T
        displayed["cartesian_rotations"] = frame @ payload["cartesian_rotations"] @ frame.T
        native_repaired = project_operators(payload)
        frame_repaired = project_operators(displayed)
        assert_allclose(native_repaired["rvec"], frame_repaired["rvec"])
        assert_allclose(native_repaired["ham"], frame_repaired["ham"], atol=1e-14)
        for name in ["centers", "connection"]:
            assert_allclose(native_repaired[name] @ frame.T, frame_repaired[name], atol=1e-14)
        for native, rotated in [(payload, displayed), (dict(payload, **native_repaired), dict(displayed, **frame_repaired))]:
            energies, berry, optical = responses(native, 2)
            rotated_energies, rotated_berry, rotated_optical = responses(rotated, 2)
            assert_allclose(energies, rotated_energies, atol=1e-14)
            assert_allclose(np.linalg.det(frame) * berry @ frame.T, rotated_berry, atol=2e-13)
            assert_allclose(frame @ optical @ frame.T, rotated_optical, atol=2e-13)

    def test_included_degenerate_eigenspaces(self):
        generator = np.random.default_rng(8)
        hamiltonian = np.diag([-1, -1, 2, 2]).astype(complex)
        connection = hermitian_part(random_complex(generator, (3, 4, 4)))
        hamiltonian_derivative = hermitian_part(random_complex(generator, (3, 4, 4)))
        connection_derivative = hermitian_part(random_complex(generator, (3, 3, 4, 4)))
        arguments = (hamiltonian, connection, hamiltonian_derivative, connection_derivative, 2)
        original = point_response(*arguments)
        rotation = np.zeros((4, 4), complex)
        rotation[:2, :2] = np.linalg.qr(random_complex(generator, (2, 2)))[0]
        rotation[2:, 2:] = np.linalg.qr(random_complex(generator, (2, 2)))[0]
        with patch("response.np.linalg.eigh", return_value=(np.array([-1, -1, 2, 2]), rotation)):
            rotated = point_response(*arguments)
        for first, second in zip(original, rotated):
            assert_allclose(first, second, atol=1e-13)

    def test_empty_and_full_subspaces(self):
        payload = sample_model()
        _, berry, optical = responses(payload, 0)
        assert_allclose(berry, 0)
        assert_allclose(optical, 0)
        _, berry, optical = responses(payload, 4)
        assert_allclose(optical, 0)
        assert_allclose(finite_difference_berry(payload, 4, 1e-5), berry[0], atol=2e-8)

    def test_smoke_finite_difference(self):
        case = Path(__file__).parent.parent / "participant" / "input" / "smoke" / "model.npz"
        if not case.exists():
            self.skipTest("Supplied smoke case is not present")
        with np.load(case, allow_pickle=False) as archive:
            payload = dict(archive)
        for model in [payload, dict(payload, **project_operators(payload))]:
            _, berry, _ = responses(model, 18)
            assert_allclose(finite_difference_berry(model, 18, 2e-6), berry[0], atol=2e-7)


if __name__ == "__main__":
    unittest.main(verbosity=2)

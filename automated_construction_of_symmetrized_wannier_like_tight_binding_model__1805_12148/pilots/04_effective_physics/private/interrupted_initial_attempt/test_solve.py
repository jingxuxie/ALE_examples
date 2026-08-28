"""Independent small-system and covariance checks for the exporter."""

import itertools
import unittest

import solve
import numpy as np


def random_hermitian(random, dimension, scale=1.0):
    matrix = random.normal(size=(dimension, dimension)) + 1j * random.normal(
        size=(dimension, dimension)
    )
    return scale * (matrix + matrix.conj().T) / 2.0


def random_unitary(random, dimension):
    return solve.polar_unitary(
        random.normal(size=(dimension, dimension))
        + 1j * random.normal(size=(dimension, dimension))
    )


def canonical_exact(hamiltonian, target):
    eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
    weights = np.sum(np.abs(eigenvectors[target, :]) ** 2, axis=0)
    selected = np.argsort(weights)[-len(target):]
    projected = eigenvectors[np.ix_(target, selected)]
    rotation = solve.polar_unitary(projected)
    return (rotation * eigenvalues[selected]) @ rotation.conj().T


def evaluate(tensors, wavevector, order=3):
    result = tensors["H0"] + np.einsum("ija,a->ij", tensors["H1"], wavevector)
    result += np.einsum("ijab,a,b->ij", tensors["H2"], wavevector, wavevector)
    if order == 3:
        result += np.einsum(
            "ijabc,a,b,c->ij", tensors["H3"], wavevector, wavevector, wavevector
        )
    return result


def sample_case(seed=21):
    random = np.random.default_rng(seed)
    energy = np.array([-7.0, -4.0, -2.0, 0.3, 0.9, 2.5, 5.0, 7.0, 10.0])
    target = np.array([4, 3])
    dimension = len(target)
    unitary = random_unitary(random, dimension)
    standard = np.array([random_unitary(random, dimension) for _ in range(3)])
    antiunitary = np.array([False, False, True])
    return {
        "energy": energy,
        "momentum": np.array([random_hermitian(random, len(energy), 0.025) for _ in range(3)]),
        "spin": np.array([random_hermitian(random, dimension, 0.5) for _ in range(3)]),
        "target": target,
        "dft_repr": np.array([
            unitary @ matrix @ (unitary.T if anti else unitary.conj().T)
            for matrix, anti in zip(standard, antiunitary)
        ]),
        "standard_repr": standard,
        "antiunitary": antiunitary,
        "cart_rotation": np.tile(np.eye(3), (3, 1, 1)),
        "order": 3,
    }


class ExportTests(unittest.TestCase):
    def test_canonical_cubic_against_exact_block(self):
        case = sample_case()
        result = solve.export(case)
        direction = np.array([0.3, -0.7, 0.5])
        direction /= np.linalg.norm(direction)
        quadratic_errors = []
        cubic_errors = []
        for scale in (0.16, 0.08, 0.04):
            wavevector = scale * direction
            full = np.diag(case["energy"]).astype(complex)
            full += solve.VELOCITY * np.einsum("a,aij->ij", wavevector, case["momentum"])
            full += solve.C * (wavevector @ wavevector) * np.eye(len(full))
            exact = canonical_exact(full, case["target"])
            exact = result["U"].conj().T @ exact @ result["U"]
            quadratic_errors.append(np.linalg.norm(exact - evaluate(result, wavevector, 2)))
            cubic_errors.append(np.linalg.norm(exact - evaluate(result, wavevector, 3)))
        self.assertTrue(7.0 < quadratic_errors[-2] / quadratic_errors[-1] < 9.0)
        self.assertTrue(14.0 < cubic_errors[-2] / cubic_errors[-1] < 18.0)
        self.assertLess(cubic_errors[-1], 0.15 * quadratic_errors[-1])
        print("\nExact-block errors, quadratic:", quadratic_errors)
        print("Exact-block errors, cubic:    ", cubic_errors)

    def test_scalar_cubic_includes_retained_subtraction(self):
        energy = np.array([1.0, 5.0])
        velocity = np.zeros((3, 2, 2), dtype=complex)
        velocity[0] = [[0.7, 0.3j], [-0.3j, 1.2]]
        tensors = solve.effective_tensors(
            energy, velocity / solve.VELOCITY, np.zeros((3, 1, 1)), np.array([0]), 3
        )
        self.assertAlmostEqual(tensors["H2"][0, 0, 0, 0].real, solve.C - 0.09 / 4.0)
        self.assertAlmostEqual(tensors["H3"][0, 0, 0, 0, 0].real, 0.09 * (1.2 - 0.7) / 16.0)

    def test_magnetic_response_against_noncommuting_exact_block(self):
        random = np.random.default_rng(82)
        energy = np.array([-3.0, 0.2, 0.8, 4.0])
        target = np.array([2, 1])
        remote = np.array([0, 3])
        velocity = np.zeros((3, 4, 4), dtype=complex)
        for axis in (0, 1):
            coupling = 0.4 * (
                random.normal(size=(2, 2)) + 1j * random.normal(size=(2, 2))
            )
            velocity[axis][np.ix_(target, remote)] = coupling
            velocity[axis][np.ix_(remote, target)] = coupling.conj().T
        spin = np.array([random_hermitian(random, 2, 0.4) for _ in range(3)])
        tensors = solve.effective_tensors(energy, velocity / solve.VELOCITY, spin, target, 2)
        levels = 5
        annihilation = np.diag(np.sqrt(np.arange(1, levels)), 1)
        coordinates = (
            (annihilation + annihilation.T) / np.sqrt(2.0),
            1j * (annihilation - annihilation.T) / np.sqrt(2.0),
        )
        selected = (target[:, None] * levels + np.arange(levels)).reshape(-1)
        full_spin = np.zeros((4, 4), dtype=complex)
        full_spin[np.ix_(target, target)] = spin[2]
        coefficient = solve.C * np.kron(tensors["G"][:, :, 2], np.eye(levels))
        for first, second in itertools.product(range(2), repeat=2):
            coefficient += np.kron(
                tensors["H2"][:, :, first, second], coordinates[first] @ coordinates[second]
            )
        interior = np.array([index for index in range(2 * levels) if index % levels < levels - 1])
        errors = []
        for field in (0.004, 0.002, 0.001):
            full = np.kron(np.diag(energy), np.eye(levels)).astype(complex)
            full += solve.C * field * np.kron(full_spin, np.eye(levels))
            for axis in (0, 1):
                full += np.sqrt(field) * np.kron(velocity[axis], coordinates[axis])
                full += solve.C * field * np.kron(np.eye(4), coordinates[axis] @ coordinates[axis])
            exact = canonical_exact(full, selected)
            prediction = np.kron(np.diag(energy[target]), np.eye(levels)) + field * coefficient
            difference = (exact - prediction)[np.ix_(interior, interior)]
            errors.append(np.linalg.norm(difference))
        self.assertTrue(3.5 < errors[-2] / errors[-1] < 4.5)
        self.assertLess(errors[-1] / 0.001, 0.01)
        print("Noncommuting magnetic block errors:", errors)

    def test_tensor_symmetry_and_order_two(self):
        case = sample_case()
        result = solve.export(case)
        for name in ("H0", "H1", "H2", "H3", "G"):
            tensor = result[name]
            np.testing.assert_allclose(tensor, tensor.swapaxes(0, 1).conj(), atol=1e-13)
        np.testing.assert_allclose(result["H2"], result["H2"].swapaxes(2, 3), atol=1e-13)
        for permutation in itertools.permutations((2, 3, 4)):
            np.testing.assert_allclose(result["H3"], result["H3"].transpose((0, 1) + permutation), atol=1e-13)
        case["order"] = 2
        second_order = solve.export(case)
        self.assertFalse(np.any(second_order["H3"]))
        for name in ("U", "H0", "H1", "H2", "G"):
            np.testing.assert_allclose(result[name], second_order[name], atol=1e-13)

    def test_cartesian_rotation_and_reflection(self):
        case = sample_case()
        original = solve.export(case)
        random = np.random.default_rng(8)
        orthogonal, _ = np.linalg.qr(random.normal(size=(3, 3)))
        wavevector = np.array([0.04, -0.09, 0.07])
        for handedness in (1.0, -1.0):
            rotation = orthogonal.copy()
            rotation[0] *= handedness
            transformed = dict(case)
            transformed["momentum"] = np.einsum("ab,bij->aij", rotation, case["momentum"])
            transformed["spin"] = np.linalg.det(rotation) * np.einsum("ab,bij->aij", rotation, case["spin"])
            result = solve.export(transformed)
            np.testing.assert_allclose(
                evaluate(result, wavevector), evaluate(original, rotation.T @ wavevector), atol=1e-12
            )
            np.testing.assert_allclose(
                result["G"], np.linalg.det(rotation) * np.einsum("ab,ijb->ija", rotation, original["G"]), atol=1e-12
            )

    def test_degenerate_remote_and_target_gauge_covariance(self):
        random = np.random.default_rng(101)
        energy = np.array([-3.0, -3.0, 0.2, 0.2, 4.0, 4.0])
        target = np.array([3, 2])
        momentum = np.array([random_hermitian(random, 6, 0.02) for _ in range(3)])
        spin = np.array([random_hermitian(random, 2) for _ in range(3)])
        full_gauge = np.zeros((6, 6), dtype=complex)
        for start in (0, 2, 4):
            full_gauge[start:start + 2, start:start + 2] = random_unitary(random, 2)
        target_gauge = full_gauge[np.ix_(target, target)]
        changed_momentum = full_gauge.conj().T @ momentum @ full_gauge
        changed_spin = target_gauge.conj().T @ spin @ target_gauge
        original = solve.effective_tensors(energy, momentum, spin, target, 3)
        changed = solve.effective_tensors(energy, changed_momentum, changed_spin, target, 3)
        for name, tensor in original.items():
            expected = np.einsum("pi,pq...,qj->ij...", target_gauge.conj(), tensor, target_gauge)
            np.testing.assert_allclose(changed[name], expected, atol=1e-12)

    def test_all_bands_retained_and_degeneracy_rejected(self):
        case = sample_case()
        target = np.arange(len(case["energy"]))[::-1]
        spin = np.zeros((3, len(target), len(target)), dtype=complex)
        result = solve.effective_tensors(case["energy"], case["momentum"], spin, target, 3)
        np.testing.assert_allclose(result["H2"], solve.C * np.einsum("ij,ab->ijab", np.eye(len(target)), np.eye(3)))
        self.assertFalse(np.any(result["H3"]))
        with self.assertRaisesRegex(ValueError, "degenerate"):
            solve.effective_tensors(np.zeros(2), np.zeros((3, 2, 2)), np.zeros((3, 1, 1)), np.array([0]), 3)


class BasisTests(unittest.TestCase):
    def check_basis(self, standard, antiunitary, random, noise=0.0):
        dimension = standard.shape[1]
        known = random_unitary(random, dimension)
        supplied = np.array([
            known @ matrix @ (known.T if anti else known.conj().T)
            for matrix, anti in zip(standard, antiunitary)
        ])
        supplied += noise * (
            random.normal(size=supplied.shape) + 1j * random.normal(size=supplied.shape)
        )
        recovered = solve.recover_basis(supplied, standard, np.array(antiunitary))
        np.testing.assert_allclose(recovered.conj().T @ recovered, np.eye(dimension), atol=2e-12)
        residual = np.linalg.norm([
            matrix @ (recovered.conj() if anti else recovered) - recovered @ reference
            for matrix, reference, anti in zip(supplied, standard, antiunitary)
        ])
        self.assertLess(residual, max(2e-12, 5 * dimension * np.sqrt(len(standard)) * noise))

    def test_generic_unitary_and_antiunitary_constraints(self):
        random = np.random.default_rng(11)
        for dimension in (1, 2, 3, 4):
            for antiunitary in ([False], [True], [False, False], [False, True]):
                standard = np.array([random_unitary(random, dimension) for _ in antiunitary])
                self.check_basis(standard, antiunitary, random)

    def test_reducible_repeated_kramers_and_noisy_representations(self):
        random = np.random.default_rng(29)
        pauli_z = np.diag([1.0, -1.0])
        kramers = np.array([[0.0, 1.0], [-1.0, 0.0]])
        representations = [
            (np.array([np.diag(np.exp(1j * np.array([0.2, 0.2, 1.3, 2.1])))]), [False]),
            (np.array([np.eye(4)]), [True]),
            (np.array([np.kron(np.eye(2), kramers)]), [True]),
            (np.array([np.kron(np.eye(2), 1j * pauli_z), np.kron(np.eye(2), kramers)]), [False, True]),
            (np.array([np.eye(4)]), [False]),
        ]
        for standard, antiunitary in representations:
            for noise in (0.0, 1e-7, 1e-5):
                self.check_basis(standard.astype(complex), antiunitary, random, noise)

    def test_no_generators(self):
        recovered = solve.recover_basis(np.empty((0, 4, 4)), np.empty((0, 4, 4)), np.empty(0, dtype=bool))
        np.testing.assert_array_equal(recovered, np.eye(4))


if __name__ == "__main__":
    unittest.main(verbosity=2)

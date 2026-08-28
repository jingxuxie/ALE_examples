"""Independent formula checks and public-fixture invariance tests."""

import itertools
from pathlib import Path
import unittest

import numpy as np

from solve import solve


def direct_tensor(data, triplet):
    representatives = data["p2s_map"]
    primitive_count = len(representatives)
    supercell_count = len(data["s2p_map"])
    dense_map = [
        list(representatives).index(representative)
        for representative in data["s2p_map"]
    ]
    force_constants = data["fc3"]
    origins = []
    for order in [(0, 1, 2), (1, 0, 2), (2, 1, 0)]:
        ordered = triplet[list(order)]
        origin = np.zeros((primitive_count,) * 3 + (3,) * 3, complex)
        for anchor in range(primitive_count):
            phase = np.empty((2, supercell_count), complex)
            for superatom in range(supercell_count):
                count, offset = data["multiplicities"][superatom, anchor]
                for leg in range(2):
                    phase[leg, superatom] = sum(
                        np.exp(2j * np.pi * np.dot(ordered[leg + 1], vector))
                        for vector in data["shortest_vectors"][offset:offset + count]
                    ) / count
            row = anchor if force_constants.shape[0] == primitive_count else representatives[anchor]
            relative_position = data["primitive_positions"][anchor] - data["primitive_positions"][0]
            prephase = np.exp(2j * np.pi * np.dot(ordered.sum(axis=0), relative_position))
            for second in range(supercell_count):
                for third in range(supercell_count):
                    origin[anchor, dense_map[second], dense_map[third]] += (
                        force_constants[row, second, third]
                        * prephase * phase[0, second] * phase[1, third]
                    )
        origins.append(origin)
    tensor = np.empty_like(origins[0])
    for first, second, third in itertools.product(range(primitive_count), repeat=3):
        for alpha, beta, gamma in itertools.product(range(3), repeat=3):
            tensor[first, second, third, alpha, beta, gamma] = (
                origins[0][first, second, third, alpha, beta, gamma]
                + origins[1][second, first, third, beta, alpha, gamma]
                + origins[2][third, second, first, gamma, beta, alpha]
            ) / 3.0
    return tensor


def direct_strengths(data, tensor, triplet_index):
    masses = data["masses"]
    primitive_count = len(masses)
    band_count = primitive_count * 3
    frequencies = data["frequencies"][triplet_index]
    eigenvectors = data["eigenvectors"][triplet_index]
    strengths = np.zeros((band_count,) * 3)
    for first, second, third in itertools.product(range(band_count), repeat=3):
        selected = frequencies[0, first], frequencies[1, second], frequencies[2, third]
        if not all(value > data["cutoff_frequency"] for value in selected):
            continue
        first_vector = eigenvectors[0, :, first].reshape(primitive_count, 3) / np.sqrt(masses[:, None])
        second_vector = eigenvectors[1, :, second].reshape(primitive_count, 3) / np.sqrt(masses[:, None])
        third_vector = eigenvectors[2, :, third].reshape(primitive_count, 3) / np.sqrt(masses[:, None])
        amplitude = np.sum(
            tensor
            * first_vector[:, None, None, :, None, None]
            * second_vector[None, :, None, None, :, None]
            * third_vector[None, None, :, None, None, :]
        )
        strengths[first, second, third] = abs(amplitude) ** 2 / np.prod(selected)
    return strengths


def random_case(primitive_count, seed):
    random = np.random.default_rng(seed)
    supercell_count = primitive_count * 3
    band_count = primitive_count * 3
    atom_order = random.permutation(supercell_count)
    representatives = atom_order[:primitive_count]
    dense_map = np.empty(supercell_count, dtype=np.int64)
    for cell in range(3):
        dense_map[atom_order[cell * primitive_count:(cell + 1) * primitive_count]] = np.arange(primitive_count)
    multiplicities = np.empty((supercell_count, primitive_count, 2), dtype=np.int64)
    vectors = []
    for flattened in random.permutation(supercell_count * primitive_count):
        superatom, anchor = divmod(int(flattened), primitive_count)
        count = random.integers(1, 9)
        multiplicities[superatom, anchor] = count, len(vectors)
        vectors.extend(random.normal(size=(count, 3)))
    triplets = random.uniform(-2.0, 2.0, size=(3, 3, 3))
    reciprocal_vectors = np.array([[0, 0, 0], [2, -1, 3], [-1, 0, 1]])
    triplets[:, 2] = reciprocal_vectors - triplets[:, :2].sum(axis=1)
    eigenvectors = random.normal(size=(3, 3, band_count, band_count)) + 1j * random.normal(size=(3, 3, band_count, band_count))
    for triplet in range(3):
        for leg in range(3):
            eigenvectors[triplet, leg] = np.linalg.qr(eigenvectors[triplet, leg])[0]
    frequencies = random.uniform(0.7, 5.0, size=(3, 3, band_count))
    frequencies[0, 0, 0] = -1.0
    frequencies[0, 1, 1] = 0.0
    frequencies[0, 2, 2] = 0.5
    frequencies[1, 0, 0] = np.nextafter(0.5, np.inf)
    return {
        "fc3": random.normal(size=(primitive_count, supercell_count, supercell_count, 3, 3, 3)),
        "p2s_map": representatives,
        "s2p_map": representatives[dense_map],
        "shortest_vectors": np.asarray(vectors),
        "multiplicities": multiplicities,
        "primitive_positions": random.uniform(-1.0, 2.0, size=(primitive_count, 3)),
        "masses": random.uniform(1.0, 80.0, size=primitive_count),
        "qpoints": triplets,
        "eigenvectors": eigenvectors,
        "frequencies": frequencies,
        "cutoff_frequency": np.array(0.5),
    }


class SolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        public_input = Path(__file__).resolve().parent.parent / "participant/input/smoke.npz"
        with np.load(public_input, allow_pickle=False) as archive:
            cls.smoke = {key: archive[key] for key in archive.files}

    def test_independent_randomized_oracle(self):
        for primitive_count in [1, 2, 3]:
            with self.subTest(primitive_count=primitive_count):
                data = random_case(primitive_count, primitive_count + 103)
                result = solve(data)
                for index, triplet in enumerate(data["qpoints"]):
                    tensor = direct_tensor(data, triplet)
                    strengths = direct_strengths(data, tensor, index)
                    np.testing.assert_allclose(result["reciprocal_fc3"][index], tensor, rtol=2e-12, atol=2e-12)
                    np.testing.assert_allclose(result["coupling_strength"][index], strengths, rtol=3e-12, atol=2e-14)
                self.assertTrue((result["coupling_strength"][0, 0] == 0).all())
                self.assertTrue((result["coupling_strength"][0, :, 1] == 0).all())
                self.assertTrue((result["coupling_strength"][0, :, :, 2] == 0).all())
                self.assertGreater(result["coupling_strength"][1, 0].max(), 0.0)

    def test_full_storage_and_supercell_reordering(self):
        data = random_case(3, 421)
        expected = solve(data)
        supercell_count = len(data["s2p_map"])
        full = np.zeros((supercell_count,) + data["fc3"].shape[1:])
        full[data["p2s_map"]] = data["fc3"]
        expanded = dict(data, fc3=full)
        actual = solve(expanded)
        for key in expected:
            np.testing.assert_array_equal(actual[key], expected[key])
        order = np.random.default_rng(452).permutation(supercell_count)
        inverse = np.argsort(order)
        reordered = dict(
            data,
            p2s_map=inverse[data["p2s_map"]],
            s2p_map=inverse[data["s2p_map"][order]],
            fc3=data["fc3"][:, order][:, :, order],
            multiplicities=data["multiplicities"][order],
        )
        actual = solve(reordered)
        for key in expected:
            np.testing.assert_allclose(actual[key], expected[key], rtol=2e-12, atol=2e-12)

    def test_public_smoke_and_umklapp(self):
        data = dict(self.smoke)
        data["qpoints"] = data["qpoints"].copy()
        data["qpoints"][0, 0] += [1, -2, 0]
        for current in [self.smoke, data]:
            result = solve(current)
            tensor = direct_tensor(current, current["qpoints"][0])
            strengths = direct_strengths(current, tensor, 0)
            np.testing.assert_allclose(result["reciprocal_fc3"][0], tensor, rtol=3e-12, atol=2e-12)
            np.testing.assert_allclose(result["coupling_strength"][0], strengths, rtol=3e-12, atol=2e-16)

    def test_triplet_permutations(self):
        data = dict(self.smoke)
        data["qpoints"] = data["qpoints"].copy()
        data["qpoints"][0, 0] += [2, -1, 1]
        original = solve(data)
        for order in itertools.permutations(range(3)):
            permuted = dict(data)
            for key in ["qpoints", "frequencies", "eigenvectors"]:
                permuted[key] = data[key][:, list(order)]
            actual = solve(permuted)
            tensor_axes = (0,) + tuple(1 + axis for axis in order) + tuple(4 + axis for axis in order)
            band_axes = (0,) + tuple(1 + axis for axis in order)
            np.testing.assert_allclose(actual["reciprocal_fc3"], original["reciprocal_fc3"].transpose(tensor_axes), rtol=1e-11, atol=1e-11)
            np.testing.assert_allclose(actual["coupling_strength"], original["coupling_strength"].transpose(band_axes), rtol=1e-11, atol=1e-16)

    def test_time_reversal_and_origin_shift(self):
        data = random_case(3, 274)
        original = solve(data)
        reversed_data = dict(data, qpoints=-data["qpoints"], eigenvectors=data["eigenvectors"].conj())
        reversed_result = solve(reversed_data)
        np.testing.assert_allclose(reversed_result["reciprocal_fc3"], original["reciprocal_fc3"].conj(), rtol=2e-12, atol=2e-12)
        np.testing.assert_allclose(reversed_result["coupling_strength"], original["coupling_strength"], rtol=2e-12, atol=2e-14)
        shifted = solve(dict(data, primitive_positions=data["primitive_positions"] + [0.371, -1.271, 0.192]))
        for key in original:
            np.testing.assert_allclose(shifted[key], original[key], rtol=2e-12, atol=2e-12)

    def test_primitive_reordering_reference_phase(self):
        data = random_case(3, 631)
        original = solve(data)
        order = np.array([2, 0, 1])
        rows = (3 * order[:, None] + np.arange(3)).ravel()
        reordered = dict(
            data,
            p2s_map=data["p2s_map"][order],
            fc3=data["fc3"][order],
            multiplicities=data["multiplicities"][:, order],
            primitive_positions=data["primitive_positions"][order],
            masses=data["masses"][order],
            eigenvectors=data["eigenvectors"][:, :, rows],
        )
        actual = solve(reordered)
        expected = original["reciprocal_fc3"][:, order][:, :, order][:, :, :, order]
        shift = data["primitive_positions"][0] - data["primitive_positions"][order[0]]
        phase = np.exp(2j * np.pi * (data["qpoints"].sum(axis=1) @ shift))
        expected = expected * phase[:, None, None, None, None, None, None]
        np.testing.assert_allclose(actual["reciprocal_fc3"], expected, rtol=3e-12, atol=3e-12)
        np.testing.assert_allclose(actual["coupling_strength"], original["coupling_strength"], rtol=3e-12, atol=2e-14)

    def test_gamma_and_mass_scaling(self):
        data = random_case(2, 517)
        data["qpoints"] = np.zeros_like(data["qpoints"])
        original = solve(data)
        self.assertTrue((original["reciprocal_fc3"].imag == 0).all())
        scaled = solve(dict(data, masses=data["masses"] * 4.0))
        np.testing.assert_allclose(scaled["coupling_strength"], original["coupling_strength"] / 64.0, rtol=2e-12, atol=2e-14)

    def test_all_invalid_and_empty_triplets(self):
        data = random_case(2, 968)
        data["frequencies"] = np.full_like(data["frequencies"], data["cutoff_frequency"])
        self.assertTrue((solve(data)["coupling_strength"] == 0).all())
        for key in ["qpoints", "eigenvectors", "frequencies"]:
            data[key] = data[key][:0]
        actual = solve(data)
        self.assertEqual(actual["reciprocal_fc3"].shape, (0, 2, 2, 2, 3, 3, 3))
        self.assertEqual(actual["coupling_strength"].shape, (0, 6, 6, 6))


if __name__ == "__main__":
    unittest.main(verbosity=2)

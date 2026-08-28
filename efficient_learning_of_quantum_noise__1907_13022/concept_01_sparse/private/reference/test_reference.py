import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
from pathlib import Path
import tempfile
import unittest

import numpy as np

from build import generate_case, observations, sampling_hash, transform
from metrics import load_output, measure, rational
from physical import characters, masks_to_observables, spectrum
from solver import reconstruct, walsh


class ReferenceTests(unittest.TestCase):
    def test_walsh_against_explicit_matrix(self):
        generator = np.random.default_rng(27)
        values = generator.normal(size=(3, 16))
        matrix = np.array([[(-1) ** (left & right).bit_count() for right in range(16)] for left in range(16)])
        np.testing.assert_allclose(walsh(values), values @ matrix)
        np.testing.assert_allclose(transform(values), values @ matrix)

    def test_physical_pauli_commutation(self):
        paulis = np.arange(4, dtype=np.uint8)[:, None]
        expected = np.array([[1, 1, 1, 1], [1, 1, -1, -1], [1, -1, 1, -1], [1, -1, -1, 1]])
        np.testing.assert_array_equal(characters(paulis, paulis), expected)

    def test_dense_small_physical_truth(self):
        generator = np.random.default_rng(531)
        qubits = 3
        labels = np.array(list(itertools.product(range(4), repeat=qubits)), dtype=np.uint8)
        probabilities = generator.dirichlet(np.ones(len(labels)))
        lookup = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
        bits = lookup[labels].reshape(len(labels), 2 * qubits)
        hashes = np.array([sampling_hash(generator, qubits, qubits)])
        offsets = np.array(list(itertools.product(range(2), repeat=2 * qubits)), dtype=np.uint8)
        actual = observations(bits, probabilities, 0.0, hashes, offsets)[0]
        binary = ((np.arange(2**qubits)[:, None] >> np.arange(qubits)) & 1).astype(np.uint8)
        for index, offset in enumerate(offsets):
            masks = offset ^ ((binary @ hashes[0]) & 1)
            expected = spectrum(labels, probabilities, 0.0, masks_to_observables(masks))
            np.testing.assert_allclose(actual[index], expected, atol=1e-14)
        self.assertAlmostEqual(float(spectrum(labels, probabilities, 0.0, np.zeros((1, qubits), dtype=np.uint8))[0]), 1.0)

    def test_hashes_are_commuting_and_full_rank(self):
        generator = np.random.default_rng(531)
        matrix = sampling_hash(generator, 40, 7)
        symplectic = (matrix[:, 0::2] @ matrix[:, 1::2].T + matrix[:, 1::2] @ matrix[:, 0::2].T) & 1
        self.assertFalse(np.any(symplectic))
        combinations = ((np.arange(128)[:, None] >> np.arange(7)) & 1).astype(np.uint8)
        self.assertEqual(len(np.unique((combinations @ matrix) & 1, axis=0)), 128)

    def test_rational_is_strictly_decreasing_uncapped(self):
        scores = [rational(loss, 0.04, 1.4) for loss in (0.0, 0.01, 0.1, 1.0, 2.0, 5.0, 20.0)]
        self.assertTrue(all(left > right for left, right in zip(scores, scores[1:])))

    def test_reconstructs_fresh_observations(self):
        data, truth, metadata = generate_case(812853, "dynamic_range", 0, example=True)
        prediction = reconstruct(data)
        metrics = measure(prediction, truth, float(data["recovery_floor"]))
        self.assertGreater(metrics["recovery_score"], 0.98)
        self.assertLess(metrics["probability_relative_l1"], 0.02)
        changed = dict(data)
        changed["eigenvalues"] = np.ones_like(data["eigenvalues"])
        empty = reconstruct(changed)
        self.assertEqual(len(empty["paulis"]), 0)
        self.assertGreater(len(prediction["paulis"]), 50)

    def test_seed_region_and_public_schema(self):
        first, truth, metadata = generate_case(43, "collisions", 0, example=True)
        second, other, metadata = generate_case(43, "collisions", 0, region="heldout", example=True)
        self.assertFalse(np.array_equal(first["hashes"], second["hashes"]))
        self.assertFalse(np.array_equal(truth["paulis"], other["paulis"]))
        self.assertEqual(set(first), {"n_qubits", "hashes", "offsets", "eigenvalues", "noise_std", "recovery_floor", "max_terms"})

    def test_invalid_output_rejected(self):
        root = Path(__file__).resolve().parents[2] / "attempt"
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            path = Path(temporary) / "bad.npz"
            np.savez(path, paulis=np.ones((2, 40), dtype=np.uint8), probabilities=np.array([0.1, 0.1]), p_identity=np.array(0.8))
            with self.assertRaises(ValueError):
                load_output(path, 40, 512)

    def test_symlink_output_rejected(self):
        root = Path(__file__).resolve().parents[2] / "attempt"
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            target = Path(temporary) / "answer.npz"
            np.savez(target, paulis=np.ones((1, 40), dtype=np.uint8), probabilities=np.array([0.1]), p_identity=np.array(0.9))
            linked = Path(temporary) / "output.npz"
            linked.symlink_to(target)
            with self.assertRaises(ValueError):
                load_output(linked, 40, 512)


if __name__ == "__main__":
    unittest.main()

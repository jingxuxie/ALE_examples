import unittest
import numpy as np
import solver


class SolverTests(unittest.TestCase):
    def test_hadamard(self):
        random = np.random.default_rng(843)
        for qubits in range(1, 8):
            values = random.normal(size=(4, 1 << qubits))
            np.testing.assert_allclose(solver.hadamard(solver.hadamard(values)) / (1 << qubits), values, atol=2e-14)

    def test_spam_and_irregular_shots(self):
        random = np.random.default_rng(811)
        for qubits in [1, 3, 7]:
            size = 1 << qubits
            channel = random.dirichlet(np.ones(size)) * 0.06
            channel[0] += 0.94
            spam = random.dirichlet(np.ones(size)) * 0.3
            spam[0] += 0.7
            depths = np.array([0, 3, 9, 14, 27, 53])
            rows = solver.hadamard(solver.hadamard(spam)[None, :] * solver.hadamard(channel)[None, :] ** depths[:, None]) / size
            counts = np.round(rows * np.array([1e11, 3e11, 1.4e11, 8e10, 2e11, 1e11])[:, None])
            recovered = solver.reconstruct(counts, depths)
            np.testing.assert_allclose(recovered, channel, atol=1e-7)
            np.testing.assert_allclose(solver.reconstruct(counts[[4, 0, 3, 5, 2, 1]], depths[[4, 0, 3, 5, 2, 1]]), recovered, atol=1e-12)

    def test_signed_modes(self):
        for channel in [np.array([0.2, 0.8]), np.array([0.9, 0.1]), np.array([0.49, 0.51]), np.array([0.5, 0.5])]:
            for spam in [np.array([0.8, 0.2]), np.array([0.1, 0.9])]:
                depths = np.array([0, 1, 3, 6, 8, 11])
                rows = solver.hadamard(solver.hadamard(spam)[None, :] * solver.hadamard(channel)[None, :] ** depths[:, None]) / 2
                recovered = solver.reconstruct(np.round(rows * 1e10), depths)
                np.testing.assert_allclose(recovered, channel, atol=1e-7)

    def test_late_nonexponential_tail(self):
        channel = np.array([0.94, 0.015, 0.013, 0.006, 0.014, 0.003, 0.005, 0.004])
        spam = np.array([0.70, 0.06, 0.05, 0.04, 0.07, 0.03, 0.03, 0.02])
        depths = np.array([0, 1, 3, 8, 15, 30, 55, 85, 300, 500])
        rows = solver.hadamard(solver.hadamard(spam)[None, :] * solver.hadamard(channel)[None, :] ** depths[:, None]) / 8
        rows[-2:] = 0.9 * rows[-2:] + 0.1 * spam
        recovered = solver.reconstruct(np.round(rows * 1e12), depths)
        np.testing.assert_allclose(recovered, channel, atol=1e-7)

    def test_categorical_information(self):
        states = np.arange(8)
        distribution = np.array([0.25 if int(state).bit_count() % 2 == 0 else 0.0 for state in states])
        blocks = np.eye(3, dtype=np.uint8)
        queries = np.array([[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                            [[1, 0, 0], [0, 1, 0], [0, 0, 0]],
                            [[1, 1, 0], [0, 0, 1], [0, 0, 0]]])
        parents = np.zeros((3, 3), dtype=np.uint8)
        correlations, information, distance = solver.diagnostics(distribution, blocks, queries, parents)
        np.testing.assert_allclose(correlations, np.eye(3), atol=1e-12)
        np.testing.assert_allclose(information, [np.log(2), 0, np.log(2)], atol=1e-12)
        self.assertAlmostEqual(float(distance), np.sqrt(0.31127812445913283))
        parents[2, :2] = 1
        self.assertLess(solver.diagnostics(distribution, blocks, queries, parents)[2], 1e-7)
        for state in [0, 7]:
            correlations, information, distance = solver.diagnostics(np.eye(8)[state], blocks, queries, parents)
            np.testing.assert_allclose(correlations, 0)
            np.testing.assert_allclose(information, 0)
            self.assertLess(distance, 1e-7)

    def test_group_events(self):
        distribution = np.array([0.7, 0.05, 0.03, 0.04, 0.06, 0.02, 0.03, 0.07])
        blocks = np.array([[1, 1, 0], [0, 0, 1]])
        correlations, information, distance = solver.diagnostics(distribution, blocks, np.zeros((0, 3, 3)), np.zeros((3, 3)))
        mean_first, mean_second = 0.24, 0.18
        covariance = 0.12 - mean_first * mean_second
        expected = covariance / np.sqrt(mean_first * (1 - mean_first) * mean_second * (1 - mean_second))
        self.assertAlmostEqual(correlations[0, 1], expected)
        self.assertEqual(information.shape, (0,))

    def test_empty_and_duplicate_depths(self):
        rows = np.array([[100.0, 0.0], [100.0, 0.0], [100.0, 0.0], [0.0, 0.0]])
        np.testing.assert_allclose(solver.reconstruct(rows, np.array([0, 0, 4, 10])), [1, 0])
        np.testing.assert_allclose(solver.reconstruct(rows[:1], np.array([0])), [1, 0])

    def test_missing_parent_configurations(self):
        distribution = np.zeros(8)
        distribution[[0, 7]] = 0.5
        parents = np.zeros((3, 3), dtype=np.uint8)
        parents[2, :2] = 1
        result = solver.diagnostics(distribution, np.eye(3), np.zeros((0, 3, 3)), parents)
        self.assertAlmostEqual(float(result[2]), np.sqrt(0.31127812445913283))

    def test_non_topological_dag(self):
        distribution = []
        for state in range(8):
            root, middle, leaf = (state >> 2) & 1, state & 1, (state >> 1) & 1
            root_probability = 0.4 if root else 0.6
            middle_probability = 0.8 if root else 0.1
            leaf_probability = 0.7 if middle else 0.2
            distribution.append(root_probability * (middle_probability if middle else 1 - middle_probability)
                                * (leaf_probability if leaf else 1 - leaf_probability))
        parents = np.zeros((3, 3), dtype=np.uint8)
        parents[0, 2] = 1
        parents[1, 0] = 1
        result = solver.diagnostics(np.array(distribution), np.eye(3), np.zeros((0, 3, 3)), parents)
        self.assertLess(result[2], 1e-7)


if __name__ == '__main__':
    unittest.main()

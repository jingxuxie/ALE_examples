import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np
from solution import Model, integer_allocation

input_directory = Path(__file__).resolve().parents[2] / 'participant' / 'input'
if not input_directory.is_dir():
    input_directory = Path(os.environ.get('DETECTOR_INPUT_DIR', '/participant/input'))
reference_spec = importlib.util.spec_from_file_location('reference_model', input_directory / 'model.py')
reference_module = importlib.util.module_from_spec(reference_spec)
reference_spec.loader.exec_module(reference_module)


class NumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = json.loads((input_directory / 'training.json').read_text())['episodes']

    def test_probabilities_and_derivatives(self):
        for episode in self.episodes:
            model = Model(episode['spec'])
            reference = reference_module.Model(episode['spec'])
            log_rates = np.log(episode['rates'])
            probability, derivative = model.distribution(log_rates, True)
            expected_probability, expected_derivative = reference.distribution(log_rates, True)
            np.testing.assert_allclose(probability, expected_probability, atol=1e-13, rtol=1e-10)
            np.testing.assert_allclose(derivative, expected_derivative, atol=1e-13, rtol=1e-9)
            np.testing.assert_allclose(probability.sum(axis=1), 1, atol=1e-11)

    def test_batched_likelihood(self):
        rng = np.random.default_rng(7172)
        for episode in self.episodes:
            model = Model(episode['spec'])
            reference = reference_module.Model(episode['spec'])
            log_rates = np.log(episode['rates'])
            counts = rng.poisson(1000 * model.distribution(log_rates))
            points = rng.normal(log_rates, 0.15, size=(17, len(log_rates)))
            expected = np.array([np.sum(counts * np.log(reference.distribution(point))) for point in points])
            np.testing.assert_allclose(model.log_likelihood_batch(counts, points), expected,
                                       atol=1e-7, rtol=1e-12)

    def test_integer_budget(self):
        rng = np.random.default_rng(87843)
        for total in (1, 29, 100, 4200, 14000, 40000):
            for iteration in range(50):
                fractions = rng.dirichlet(np.ones(29))
                allocation = integer_allocation(fractions, total)
                self.assertEqual(int(allocation.sum()), total)
                self.assertTrue(np.all(allocation >= 0))
                self.assertTrue(np.all(np.abs(allocation - total * fractions) <= 1))


if __name__ == '__main__':
    unittest.main()

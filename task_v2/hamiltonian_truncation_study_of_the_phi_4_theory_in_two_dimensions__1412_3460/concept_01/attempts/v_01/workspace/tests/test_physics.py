import math
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import sparse

from generated import generate
from numerics import diagonalize, hamiltonian
from physics import circle_constants, gaussian_vacuum, physical_couplings
from tails import SpectralTail


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=os.environ.get('TEST_OUTPUT', '.'))
        self.case = {'length': 4.0, 'mass': 1.0, 'boundary': 'periodic',
                     'couplings': [{'degree': 2, 'value': 0.1}]}

    def tearDown(self):
        self.directory.cleanup()

    def test_independent_gaussian_calibration(self):
        mass, vacuum = gaussian_vacuum(self.case)
        self.assertAlmostEqual(vacuum, -0.005822191596577913, places=13)
        self.assertAlmostEqual(mass, 1.0954451150103321, places=13)

    def test_boundary_and_wick_conversion(self):
        difference, periodic_vacuum = circle_constants(1, 4, 'periodic')
        twisted_difference, twisted_vacuum = circle_constants(1, 4, 'antiperiodic')
        self.assertGreater(difference, 0)
        self.assertLess(twisted_difference, 0)
        self.assertLess(periodic_vacuum, 0)
        self.assertGreater(twisted_vacuum, 0)
        case = dict(self.case, couplings=[{'degree': 4, 'value': 1.2}, {'degree': 3, 'value': -0.4}])
        coefficients, constant = physical_couplings(case)
        self.assertAlmostEqual(coefficients[(2, 0)], 7.2 * difference)
        self.assertAlmostEqual(coefficients[(1, 0)], -1.2 * difference)
        self.assertAlmostEqual(constant, periodic_vacuum + 4 * 3.6 * difference ** 2)

    def test_gaussian_truncated_variational_bound(self):
        sector = {'momentum': 0, 'parity': 0}
        basis = generate(self.case, sector, 14, [(2, 0)], self.directory.name)
        coefficients, constant = physical_couplings(self.case)
        numerical = diagonalize(hamiltonian(basis, coefficients, constant))[0]
        exact = gaussian_vacuum(self.case)[1]
        self.assertGreater(numerical, exact)
        self.assertLess(numerical - exact, 1e-4)

    def test_spectral_wick_factor_matches_explicit_elimination(self):
        for boundary in ['periodic', 'antiperiodic']:
            case = dict(self.case, boundary=boundary, couplings=[{'degree': 4, 'value': 1.0}])
            basis = generate(case, {'momentum': 0, 'parity': 0}, 20, [(4, 0)],
                             Path(self.directory.name) / boundary / 'basis')
            spectral = SpectralTail(case, {(0, 0, 4, 0): 24}, Path(self.directory.name) / boundary / 'tail')
            column = basis['operators'][(4, 0)].getcol(0).toarray().ravel()
            mask = basis['energy'] > 10 + 1e-8
            explicit = np.sum(column[mask] ** 2 / basis['energy'][mask])
            loop = 24 * case['length'] * (spectral.moments(4, 0, 10)[0] - spectral.moments(4, 0, 20)[0])
            self.assertAlmostEqual(explicit, loop, places=11)

    def test_random_seed_finds_reflection_odd_ground(self):
        vector = np.zeros(256)
        vector[0], vector[1] = 1 / math.sqrt(2), -1 / math.sqrt(2)
        matrix = 3 * sparse.eye(256, format='csr') - 4 * sparse.csr_matrix(np.outer(vector, vector))
        self.assertTrue(np.allclose(diagonalize(matrix), [-1, 3, 3], atol=1e-9))

    def test_unprojected_free_multiplicity(self):
        basis = generate(self.case, {'momentum': None, 'parity': 1}, 6, [], self.directory.name)
        values = diagonalize(sparse.diags(basis['energy'], format='csr'))
        frequency = math.hypot(1, 2 * math.pi / 4)
        self.assertTrue(np.allclose(values, [1, frequency, frequency], atol=1e-10))


if __name__ == '__main__':
    unittest.main()

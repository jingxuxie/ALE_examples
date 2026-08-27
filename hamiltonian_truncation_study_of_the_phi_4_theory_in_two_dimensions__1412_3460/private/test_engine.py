import math
from pathlib import Path
import sys

import numpy as np
from scipy import linalg

sys.path.insert(0, str(Path(__file__).parent / 'engine'))
from basis import enumerate_basis
from operators import operator_matrix
from physics import finite_volume


def test_zero_mode_matrix():
    modes, frequencies, states, energies = enumerate_basis(0.5, 1.0, 7.0, 'periodic', 0, None)
    matrix = operator_matrix(modes, frequencies, states, 0.5, 4).toarray()
    assert abs(matrix[0, 4] - math.sqrt(24) / (4 * 0.5)) < 1e-12
    assert abs(matrix[2, 2] - 12 / (4 * 0.5)) < 1e-12
    assert np.max(abs(matrix - matrix.T)) < 1e-12


def test_twisted_basis():
    modes, frequencies, states, energies = enumerate_basis(4.0, 1.0, 9.0, 'antiperiodic', 1, 1)
    assert np.all(modes % 2 == 1)
    assert np.all(states @ modes == 1)
    assert np.all(states.sum(axis=1) % 2 == 1)
    matrix = operator_matrix(modes, frequencies, states, 4.0, 4).toarray()
    assert np.max(abs(matrix - matrix.T)) < 1e-12


def test_transfer_adjoint():
    modes, frequencies, states, energies = enumerate_basis(2.5, 1.0, 9.0, 'periodic', None, 0)
    forward = operator_matrix(modes, frequencies, states, 2.5, 4, 2).toarray()
    reverse = operator_matrix(modes, frequencies, states, 2.5, 4, -2).toarray()
    assert np.max(abs(forward - reverse.T)) < 1e-12
    assert np.max(abs(forward)) > 0.0


if __name__ == '__main__':
    test_zero_mode_matrix()
    test_twisted_basis()
    test_transfer_adjoint()
    print('Three independent oscillator/boundary/transfer checks passed.')

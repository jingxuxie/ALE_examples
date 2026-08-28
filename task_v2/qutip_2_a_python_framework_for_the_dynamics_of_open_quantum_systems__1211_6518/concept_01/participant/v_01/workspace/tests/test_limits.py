import numpy as np

from oqs.baths import spectrum
from oqs.io import coefficient


def test_thermal_balance():
    bath = {'kind': 'thermal', 'eta': 0.3, 'temperature': 0.8, 'cutoff': 10.0}
    assert np.isclose(spectrum(bath, -0.6) / spectrum(bath, 0.6), np.exp(-0.6 / 0.8))
    assert np.isclose(spectrum(bath, 0), 0.24)


def test_step_boundary():
    specification = {'kind': 'steps', 'edges': [0.5], 'values': [[0.2, 0.1], [0.4, -0.3]]}
    assert coefficient(specification, 0.5) == 0.4 - 0.3j

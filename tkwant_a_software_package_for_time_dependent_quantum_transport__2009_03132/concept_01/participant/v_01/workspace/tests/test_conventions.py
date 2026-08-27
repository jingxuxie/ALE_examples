import numpy as np
from scipy import sparse
from transport.observables import measure
from transport.protocols import signal
from transport.reservoirs import fermi, surface


def test_oriented_current_is_incoming_density_derivative():
    matrix = np.array([[.2, .3 + .7j], [.3 - .7j, -.1]])
    state = np.array([[.6], [.8j]])
    case = {'hamiltonian': {'real': matrix.real.tolist()}, 'current_bonds': [[0, 1], [1, 0]]}
    density, current = measure(case, sparse.csr_matrix(matrix), state)
    derivative = 2 * np.real(state.conj() * (-1j * matrix @ state)).ravel()
    assert np.allclose(current, derivative)
    assert np.allclose(density, [.36, .64])


def test_retarded_surface_and_phase_conventions():
    energy = .7
    expected = (energy - 1j * np.sqrt(4 - energy ** 2)) / 2
    assert abs(surface(energy, np.array([[0j]]), np.array([[-1j * 0 - 1]]))[0, 0] - expected) < 1e-7
    spec = dict(amplitude=.4, duration=3., profile='voltage_phase')
    assert signal(0, spec) == 0
    assert abs(signal(5., spec) - 1.4) < 1e-12
    assert np.array_equal(fermi(np.array([-1., 0., 1.]), 0., 0.), [1., 0., 0.])

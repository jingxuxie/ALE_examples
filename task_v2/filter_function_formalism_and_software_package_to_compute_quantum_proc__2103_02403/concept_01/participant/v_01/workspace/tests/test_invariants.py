import numpy as np

from pipeline.physics import choi, ideal_channel, liouvillian


def test_column_vectorization():
    hamiltonian = np.array([[0.3, 0.2j], [-0.2j, -0.1]])
    state = np.array([[0.2, 0.1j], [-0.1j, 0.8]])
    expected = -1j * (hamiltonian @ state - state @ hamiltonian)
    actual = (liouvillian(hamiltonian) @ state.reshape(-1, order='F')).reshape((2, 2), order='F')
    np.testing.assert_allclose(actual, expected)


def test_identity_choi():
    values = np.linalg.eigvalsh(choi(np.eye(4)))
    np.testing.assert_allclose(values, [0, 0, 0, 1], atol=1e-14)


def test_control_segmentation():
    hamiltonian = np.array([[0.2, 0.4], [0.4, -0.2]])
    whole = {'H': hamiltonian[None], 'dt': np.array([1.0])}
    split = {'H': np.repeat(hamiltonian[None], 3, axis=0), 'dt': np.array([0.2, 0.5, 0.3])}
    np.testing.assert_allclose(ideal_channel(whole), ideal_channel(split), atol=1e-14)

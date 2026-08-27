import numpy as np

from cores import detect
from current import measure
from model import Model, imprint


def fixture():
    axis = np.arange(64) / 8 - 4
    xx, yy = np.meshgrid(axis, axis)
    arrays = dict(x=axis, y=axis, roi=(xx ** 2 + yy ** 2 < 9).astype(int), bulk=xx ** 2 + yy ** 2 < 4, potential=np.zeros_like(xx))
    case = dict(g=0, omega=0, correlation_edges=[0, 2, 4], spectrum_edges=[0, 1, 3, 100])
    return Model(case, arrays)


def test_phase_only():
    model = fixture()
    psi = np.exp(-(model.xx ** 2 + model.yy ** 2)) * np.exp(0.7j * model.xx)
    changed = imprint(psi, model, [dict(x=0.11, y=-0.13, charge=-1)])
    np.testing.assert_allclose(np.abs(changed), np.abs(psi), atol=1e-14)


def test_signed_core():
    model = fixture()
    psi = (model.xx - 0.043 - 1j * (model.yy + 0.031)) * np.exp(-(model.xx ** 2 + model.yy ** 2) / 2)
    cores = detect(psi, model)
    assert len(cores) == 1
    assert cores[0, 2] == -1
    assert np.linalg.norm(cores[0, :2] - [0.043, -0.031]) < 0.02


def test_uniform_flow():
    model = fixture()
    psi = np.exp(2j * np.pi * model.xx / 8) / 8
    physics = measure(psi, model, 0)
    assert abs(physics['norm'] - 1) < 1e-12
    assert abs(physics['Ei'] - (2 * np.pi / 8) ** 2 / 2) < 1e-10
    assert abs(physics['Ec']) < 1e-10

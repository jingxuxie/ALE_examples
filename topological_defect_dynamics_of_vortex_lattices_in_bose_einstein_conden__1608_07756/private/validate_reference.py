import json
import sys
from pathlib import Path

import numpy as np
from scipy.fft import fft2, ifft2
from scipy.integrate import solve_ivp


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'concept_01/solution/workspace'))
from current import measure
from model import Model
from propagate import Propagator

axis = np.arange(32) / 4 - 4
xx, yy = np.meshgrid(axis, axis)
arrays = dict(x=axis, y=axis, potential=(xx ** 2 + 1.15 * yy ** 2) / 2, roi=np.ones_like(xx), bulk=np.ones_like(xx, dtype=bool))
case = dict(g=4, omega=0.63, spectrum_edges=[0, 1, 4, 100])
model = Model(case, arrays)
initial = np.exp(-((xx - 0.2) ** 2 + (yy + 0.15) ** 2)) * np.exp(0.4j * xx)
initial /= np.sqrt(np.sum(np.abs(initial) ** 2) * model.area)


def rhs(time, flattened):
    psi = flattened.reshape(initial.shape)
    transformed = fft2(psi)
    kinetic = ifft2((model.kx ** 2 + model.ky ** 2) * transformed / 2)
    angular = -1j * (xx * ifft2(1j * model.ky * transformed) - yy * ifft2(1j * model.kx * transformed))
    return (-1j * (kinetic + (model.potential(time) + model.g * np.abs(psi) ** 2) * psi - model.omega * angular)).ravel()


exact = solve_ivp(rhs, [0, 0.3], initial.ravel(), method='DOP853', rtol=1e-10, atol=1e-12).y[:, -1].reshape(initial.shape)
errors = []
for step in [0.004, 0.002, 0.001]:
    answer = Propagator(model).evolve(initial.copy(), [0, 0.3], step)[-1]
    errors.append(float(np.linalg.norm(answer - exact) / np.linalg.norm(exact)))
physics = measure(initial, model, 0)
assert errors[1] < errors[0] * 0.3 and errors[2] < errors[1] * 0.3, errors
assert errors[2] < 1e-5, errors
print(json.dumps(dict(independent_solver='DOP853 on Fourier semidiscrete Hamiltonian',relative_errors=errors, refinement_ratios=[errors[0]/errors[1], errors[1]/errors[2]], initial_physics=physics), indent=2))

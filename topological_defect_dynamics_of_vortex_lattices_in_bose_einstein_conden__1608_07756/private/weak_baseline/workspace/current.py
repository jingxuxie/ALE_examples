import numpy as np
from scipy.fft import fft2


def measure(psi, model, time):
    density = np.abs(psi) ** 2
    phase_x = np.unwrap(np.angle(psi), axis=1)
    phase_y = np.unwrap(np.angle(psi), axis=0)
    velocity_x = np.gradient(phase_x, model.dx, axis=1)
    velocity_y = np.gradient(phase_y, model.dy, axis=0)
    weighted_x = np.sqrt(density) * velocity_x
    weighted_y = np.sqrt(density) * velocity_y
    spectrum_x = np.abs(fft2(weighted_x)) ** 2
    spectrum_y = np.abs(fft2(weighted_y)) ** 2
    magnitude = np.sqrt(model.kx ** 2 + model.ky ** 2)
    normalization = model.area / (2 * psi.size)
    edges = model.case['spectrum_edges']
    gradient_y, gradient_x = np.gradient(psi, model.dy, model.dx)
    root_y, root_x = np.gradient(np.sqrt(density), model.dy, model.dx)
    angular = np.real(np.conj(psi) * (-1j * (model.xx * gradient_y - model.yy * gradient_x)))
    kinetic = (np.abs(gradient_x) ** 2 + np.abs(gradient_y) ** 2) / 2
    return {'norm': float(density.sum() * model.area), 'r2': float(np.sum((model.xx ** 2 + model.yy ** 2) * density) * model.area), 'energy': float(model.area * np.sum(kinetic + model.potential(time) * density + model.g * density ** 2 / 2 - model.omega * angular)), 'Ec': float(normalization * spectrum_x.sum()), 'Ei': float(normalization * spectrum_y.sum()), 'Eq': float(model.area / 2 * np.sum(root_x ** 2 + root_y ** 2)), 'Ec_bins': (normalization * np.histogram(magnitude, bins=edges, weights=spectrum_x)[0]).tolist(), 'Ei_bins': (normalization * np.histogram(magnitude, bins=edges, weights=spectrum_y)[0]).tolist()}

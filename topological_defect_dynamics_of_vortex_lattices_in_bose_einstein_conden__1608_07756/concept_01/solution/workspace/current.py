import numpy as np
from scipy.fft import fft2, ifft2


def measure(psi, model, time):
    transformed = fft2(psi)
    derivative_x = ifft2(1j * model.kx * transformed)
    derivative_y = ifft2(1j * model.ky * transformed)
    density = np.abs(psi) ** 2
    root_density = np.sqrt(density)
    floor = max(float(density.max()) * 1e-12, 1e-30)
    weighted_x = np.divide(np.imag(np.conj(psi) * derivative_x), root_density, out=np.zeros_like(density), where=density > floor)
    weighted_y = np.divide(np.imag(np.conj(psi) * derivative_y), root_density, out=np.zeros_like(density), where=density > floor)
    fourier_x, fourier_y = fft2(weighted_x), fft2(weighted_y)
    magnitude2 = model.kx ** 2 + model.ky ** 2
    projection = np.divide(model.kx * fourier_x + model.ky * fourier_y, magnitude2, out=np.zeros_like(fourier_x), where=magnitude2 > 0)
    longitudinal_x = model.kx * projection
    longitudinal_y = model.ky * projection
    compressible = np.abs(longitudinal_x) ** 2 + np.abs(longitudinal_y) ** 2
    incompressible = np.abs(fourier_x - longitudinal_x) ** 2 + np.abs(fourier_y - longitudinal_y) ** 2
    normalization = model.area / (2 * psi.size)
    edges = np.asarray(model.case['spectrum_edges'])
    compressible_bins = np.histogram(np.sqrt(magnitude2), bins=edges, weights=compressible)[0] * normalization
    incompressible_bins = np.histogram(np.sqrt(magnitude2), bins=edges, weights=incompressible)[0] * normalization
    gradient_root_x = ifft2(1j * model.kx * fft2(root_density))
    gradient_root_y = ifft2(1j * model.ky * fft2(root_density))
    quantum = model.area / 2 * np.sum(np.abs(gradient_root_x) ** 2 + np.abs(gradient_root_y) ** 2)
    angular = np.real(np.conj(psi) * (-1j * (model.xx * derivative_y - model.yy * derivative_x)))
    kinetic = (np.abs(derivative_x) ** 2 + np.abs(derivative_y) ** 2) / 2
    energy = model.area * np.sum(kinetic + model.potential(time) * density + model.g / 2 * density ** 2 - model.omega * angular)
    return {
        'norm': float(model.area * density.sum()),
        'r2': float(model.area * np.sum((model.xx ** 2 + model.yy ** 2) * density)),
        'energy': float(energy),
        'Ec': float(normalization * compressible.sum()),
        'Ei': float(normalization * incompressible.sum()),
        'Eq': float(quantum),
        'Ec_bins': compressible_bins.tolist(),
        'Ei_bins': incompressible_bins.tolist(),
    }

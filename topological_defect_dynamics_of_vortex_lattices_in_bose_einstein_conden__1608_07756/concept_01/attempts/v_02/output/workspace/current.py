import numpy as np
from scipy.fft import fft2, ifft2


def measure(psi, model, time):
    density = np.abs(psi) ** 2
    amplitude = np.sqrt(density)
    transformed = fft2(psi, workers=1)
    gradient_x = ifft2(1j * model.kx * transformed, workers=1)
    gradient_y = ifft2(1j * model.ky * transformed, workers=1)
    occupied = density > 1e-12 * density.max()
    weighted_x = np.divide(np.imag(np.conj(psi) * gradient_x), amplitude,
                           out=np.zeros_like(density), where=occupied)
    weighted_y = np.divide(np.imag(np.conj(psi) * gradient_y), amplitude,
                           out=np.zeros_like(density), where=occupied)
    transformed_x = fft2(weighted_x, workers=1)
    transformed_y = fft2(weighted_y, workers=1)
    squared_k = model.kx ** 2 + model.ky ** 2
    projection = np.divide(model.kx * transformed_x + model.ky * transformed_y, squared_k,
                           out=np.zeros_like(transformed_x), where=squared_k > 0)
    compressible_x = model.kx * projection
    compressible_y = model.ky * projection
    normalization = model.area / (2 * psi.size)
    compressible = normalization * (np.abs(compressible_x) ** 2 + np.abs(compressible_y) ** 2)
    incompressible = normalization * (np.abs(transformed_x - compressible_x) ** 2
                                     + np.abs(transformed_y - compressible_y) ** 2)
    root_transformed = fft2(amplitude, workers=1)
    root_x = ifft2(1j * model.kx * root_transformed, workers=1)
    root_y = ifft2(1j * model.ky * root_transformed, workers=1)
    angular = np.real(np.conj(psi) * (-1j * (model.xx * gradient_y - model.yy * gradient_x)))
    kinetic = (np.abs(gradient_x) ** 2 + np.abs(gradient_y) ** 2) / 2
    edges = np.asarray(model.case['spectrum_edges'])
    bins = np.searchsorted(edges, np.sqrt(squared_k).ravel(), side='right') - 1
    valid = (bins >= 0) & (bins < len(edges) - 1)
    return {'norm': float(density.sum() * model.area),
            'r2': float(np.sum((model.xx ** 2 + model.yy ** 2) * density) * model.area),
            'energy': float(model.area * np.sum(kinetic + model.potential(time) * density
                                               + model.g * density ** 2 / 2 - model.omega * angular)),
            'Ec': float(compressible.sum()), 'Ei': float(incompressible.sum()),
            'Eq': float(model.area / 2 * np.sum(np.abs(root_x) ** 2 + np.abs(root_y) ** 2)),
            'Ec_bins': np.bincount(bins[valid], weights=compressible.ravel()[valid], minlength=len(edges) - 1).tolist(),
            'Ei_bins': np.bincount(bins[valid], weights=incompressible.ravel()[valid], minlength=len(edges) - 1).tolist()}

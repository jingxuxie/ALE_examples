import numpy as np
from scipy.linalg import expm

from .physics import basis_transform, ideal_channel, make_pulse, spectral_density, subset


def _forecast(case, arrays):
    import filter_functions as ff

    duration = arrays['dt'].sum()
    omega = np.geomspace(1e-3 / duration, 40 / arrays['dt'].min(), 160)
    pulse = make_pulse(arrays)
    spectrum = spectral_density(case['noise'], omega)
    cumulant = ff.numeric.calculate_cumulant_function(pulse, spectrum, omega,
                                                    second_order=False).sum(axis=(0, 1))
    transform = basis_transform(pulse.basis)
    generator = transform @ cumulant @ transform.conj().T
    return ideal_channel(arrays) @ expm(generator), generator


def predict(case, arrays, mode='selected'):
    boundaries = arrays['blocks'].astype(int)
    dimension = arrays['H'].shape[-1] ** 2
    channel = np.eye(dimension, dtype=complex)
    generator = np.zeros((dimension, dimension), dtype=complex)
    previous = np.eye(dimension, dtype=complex)
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        block = subset(arrays, begin, end)
        block_channel, block_generator = _forecast(case, block)
        generator += previous.conj().T @ block_generator @ previous
        channel = block_channel @ channel
        previous = ideal_channel(block) @ previous
    return channel, generator, {'method': 'cached_gate_forecast', 'mode': mode,
                                'block_count': len(boundaries) - 1}

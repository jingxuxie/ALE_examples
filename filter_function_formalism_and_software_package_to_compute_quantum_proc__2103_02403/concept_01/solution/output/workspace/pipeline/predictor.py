import numpy as np
from scipy.linalg import expm

from .legacy import predict as legacy_predict
from .physics import ideal_channel, subset, time_noise
from .quadratic import quadratic_response
from .reference_dynamics import solve_exact


def _selected(case, arrays, refined):
    noise = time_noise(arrays)
    generator = quadratic_response(arrays['dt'], arrays['H'], noise, case['noise'])
    if isinstance(generator, tuple):
        generator, response_diagnostics = generator
    else:
        response_diagnostics = {}
    if case['noise']['kind'] == 'broadband' and not refined:
        channel = ideal_channel(arrays) @ expm(generator)
        diagnostics = {'method': 'complete_quadratic_spectral_response',
                       'approximation': 'weak_noise_exponentiated_cumulant',
                       'response_norm': float(np.linalg.norm(generator)),
                       'settings': {'response_solver': 'piecewise_exact_moment_propagation'}}
    else:
        law = dict(case['noise'])
        if law['kind'] == 'broadband':
            law['kind'] = 'ou'
        channel, diagnostics = solve_exact(arrays['dt'], arrays['H'], noise, law,
                                           tolerance=1e-10 if refined else 1e-8)
        diagnostics.pop('noise_correction', None)
    diagnostics['response'] = response_diagnostics
    diagnostics['refined'] = bool(refined)
    return channel, generator, diagnostics


def predict(case, arrays, mode='selected'):
    if mode == 'baseline':
        return legacy_predict(case, arrays, mode)
    if mode != 'no_memory':
        return _selected(case, arrays, mode == 'refined')
    boundaries = arrays['blocks'].astype(int)
    dimension = arrays['H'].shape[-1] ** 2
    channel = np.eye(dimension, dtype=complex)
    generator = np.zeros((dimension, dimension), dtype=complex)
    previous = np.eye(dimension, dtype=complex)
    block_diagnostics = []
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        block = subset(arrays, begin, end)
        block_channel, block_generator, diagnostic = _selected(case, block, False)
        generator += previous.conj().T @ block_generator @ previous
        channel = block_channel @ channel
        previous = ideal_channel(block) @ previous
        block_diagnostics.append(diagnostic)
    return channel, generator, {'method': 'independently_restarted_baths',
                                'blocks': block_diagnostics, 'mode': mode}

import numpy as np

from .deterministic import propagate_lindblad
from .periodic import floquet_states
from .propagation import local_operators
from .spectral import redfield_states


def solve(case, options):
    channel_states = None
    if options.get('engine') == 'local':
        operators, specifications = local_operators(case)
        states = propagate_lindblad(case, case['rho0'], options, operators, specifications)
    elif case['physics'] == 'redfield':
        states = redfield_states(case, options)
    elif case['physics'] == 'floquet':
        states = floquet_states(case, options)
    elif case.get('process', False):
        dimension = len(case['H0'])
        operators = np.eye(dimension ** 2, dtype=complex).reshape(dimension, dimension, dimension ** 2, order='F')
        channel_states = propagate_lindblad(case, operators, options)
        states = np.einsum('tijb,b->tij', channel_states, case['rho0'].reshape(-1, order='F'))
    else:
        states = propagate_lindblad(case, case['rho0'], options)
    result = {'times': case['times'], 'states': states,
              'expectations': np.einsum('oij,tji->to', case['e_ops'], states)}
    if case.get('process', False):
        dimension = len(case['H0'])
        if channel_states is None:
            operators = np.eye(dimension ** 2, dtype=complex).reshape(dimension, dimension, dimension ** 2, order='F')
            channel_states = propagate_lindblad(case, operators, options)
        result['channel'] = channel_states[-1].reshape(dimension ** 2, dimension ** 2, order='F')
        choi = np.empty_like(result['channel'])
        for row in range(dimension):
            for column in range(dimension):
                choi[row * dimension:(row + 1) * dimension, column * dimension:(column + 1) * dimension] = channel_states[-1, :, :, row + column * dimension]
        result['choi'] = choi
    return result

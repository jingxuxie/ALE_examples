import numpy as np

from .propagation import propagate
from .process import process_channel


def solve(case, options):
    states = propagate(case, case['rho0'], options)
    result = {'times': case['times'], 'states': states,
              'expectations': np.einsum('oij,tji->to', case['e_ops'], states)}
    if case.get('process', False):
        result['channel'], result['choi'] = process_channel(case, options, propagate)
    return result

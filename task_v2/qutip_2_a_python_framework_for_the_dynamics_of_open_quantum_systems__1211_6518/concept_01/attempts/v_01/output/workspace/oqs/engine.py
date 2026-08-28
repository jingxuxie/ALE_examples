import numpy as np

from .propagation import propagate
from .process import channel_from_outputs, channel_to_choi, operator_basis


def solve(case, options):
    options = dict(options, _diagnostics={})
    process = case.get('process', False)
    initial = (np.concatenate((case['rho0'][None], operator_basis(len(case['H0']))))
               if process else case['rho0'])
    trajectories = propagate(case, initial, options)
    states = trajectories[:, 0] if process else trajectories
    result = {'times': case['times'], 'states': states,
              'expectations': np.einsum('oij,tji->to', case['e_ops'], states)}
    if process:
        result['channel'] = channel_from_outputs(trajectories[-1, 1:])
        result['choi'] = channel_to_choi(result['channel'])
    result.update({'solver_' + key: np.asarray(value) for key, value in options['_diagnostics'].items()})
    return result

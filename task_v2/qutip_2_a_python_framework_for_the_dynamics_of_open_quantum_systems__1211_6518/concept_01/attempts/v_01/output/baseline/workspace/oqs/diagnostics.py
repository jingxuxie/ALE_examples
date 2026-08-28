import numpy as np


def diagnostics(result):
    states = result['states']
    trace_error = np.max(np.abs(np.trace(states, axis1=1, axis2=2) - 1))
    hermiticity = np.max(np.abs(states - states.conj().transpose(0, 2, 1)))
    eigenvalue = min(float(np.linalg.eigvalsh((state + state.conj().T) / 2).min()) for state in states)
    final = states[-1]
    return {'trace_error': float(trace_error), 'hermiticity_error': float(hermiticity),
            'minimum_eigenvalue': eigenvalue,
            'final_expectation': float(result['expectations'][-1, 0].real),
            'final_purity': float(np.trace(final @ final).real)}


def distance(left, right):
    state_error = float(np.max(np.linalg.norm(left['states'] - right['states'], axis=(1, 2))))
    if 'channel' in left and 'channel' in right:
        dimension = left['states'].shape[-1]
        state_error = max(state_error, float(np.linalg.norm(left['channel'] - right['channel']) / dimension))
    return state_error

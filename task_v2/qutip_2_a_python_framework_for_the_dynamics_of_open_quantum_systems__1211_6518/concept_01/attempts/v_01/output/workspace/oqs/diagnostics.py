import numpy as np


def diagnostics(result):
    states = result['states']
    trace_error = np.max(np.abs(np.trace(states, axis1=1, axis2=2) - 1))
    hermiticity = np.max(np.abs(states - states.conj().transpose(0, 2, 1)))
    eigenvalue = min(float(np.linalg.eigvalsh((state + state.conj().T) / 2).min()) for state in states)
    final = states[-1]
    metrics = {'trace_error': float(trace_error), 'hermiticity_error': float(hermiticity),
            'minimum_eigenvalue': eigenvalue,
            'final_expectation': float(result['expectations'][-1, 0].real) if result['expectations'].shape[1] else 0.0,
            'final_purity': float(np.trace(final @ final).real)}
    if 'channel' in result:
        dimension = len(final)
        trace_vector = np.eye(dimension).ravel(order='F')
        choi = result['choi']
        marginal = np.trace(choi.reshape(dimension, dimension, dimension, dimension), axis1=1, axis2=3)
        metrics.update({'channel_trace_preservation_error': float(np.linalg.norm(trace_vector @ result['channel'] - trace_vector)),
                        'choi_trace': float(np.trace(choi).real),
                        'choi_partial_trace_error': float(np.linalg.norm(marginal - np.eye(dimension))),
                        'choi_minimum_eigenvalue': float(np.linalg.eigvalsh((choi + choi.conj().T) / 2).min())})
    metrics.update({key: float(value) for key, value in result.items() if key.startswith('solver_')})
    return metrics


def distance(left, right):
    state_error = float(np.max(np.linalg.norm(left['states'] - right['states'], axis=(1, 2))))
    if 'channel' in left and 'channel' in right:
        state_error = max(state_error, float(np.linalg.norm(left['channel'] - right['channel'])))
    return state_error

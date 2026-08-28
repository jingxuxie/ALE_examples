import numpy as np
from scipy.integrate import solve_ivp


def control_boundaries(case, start, stop):
    boundaries = [start, stop]
    for specification in case.get('h_coeffs', []) + case.get('c_coeffs', []):
        if specification['kind'] == 'steps':
            boundaries.extend(specification['edges'])
        elif specification['kind'] == 'gaussian':
            center = specification['center']
            width = specification['width']
            boundaries.extend(center + width * np.array([-8, -6, -4, -2, -1, 0, 1, 2, 4, 6, 8]))
    return np.unique([value for value in boundaries if start <= value <= stop])


def control_max_step(case, default=np.inf):
    result = default
    for specification in case.get('h_coeffs', []) + case.get('c_coeffs', []):
        if specification['kind'] in ('sin', 'cos', 'carrier'):
            frequency = abs(specification.get('omega', 1.0))
            if frequency:
                result = min(result, np.pi / (8 * frequency))
    return result


def integrate(case, derivative, initial, times, options, dense=False):
    times = np.asarray(times, dtype=float)
    if len(times) == 0 or np.any(np.diff(times) < 0):
        raise ValueError('times must be nonempty and nondecreasing')
    boundaries = control_boundaries(case, times[0], times[-1])
    current = np.asarray(initial, dtype=complex).ravel()
    result = np.empty((len(times), len(current)), dtype=complex)
    result[times == times[0]] = current
    pieces = []
    max_step = control_max_step(case, options.get('max_step', np.inf))
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        endpoint = np.nextafter(right, left)

        def bounded_derivative(time, vector):
            return derivative(min(time, endpoint), vector)

        selected = (times > left) & (times <= right)
        requested = np.unique(np.append(times[selected], right))
        solution = solve_ivp(bounded_derivative, (left, right), current,
                             method='DOP853', rtol=options['rtol'], atol=options['atol'],
                             max_step=max_step, dense_output=dense,
                             t_eval=None if dense else requested)
        if not solution.success:
            raise RuntimeError(solution.message)
        if np.any(selected):
            if dense:
                result[selected] = solution.sol(times[selected]).T
            else:
                result[selected] = solution.y[:, np.searchsorted(requested, times[selected])].T
        current = solution.y[:, -1]
        if dense:
            pieces.append(solution.sol)
    if not dense:
        return result.reshape((len(times),) + initial.shape)

    def evaluate(requested):
        requested = np.atleast_1d(requested)
        values = np.empty((len(requested), len(current)), dtype=complex)
        if not pieces:
            values[:] = current
        else:
            indices = np.clip(np.searchsorted(boundaries, requested, side='right') - 1,
                              0, len(pieces) - 1)
            for index in np.unique(indices):
                selected = indices == index
                values[selected] = pieces[index](requested[selected]).T
        return values.reshape((len(requested),) + initial.shape)

    return result.reshape((len(times),) + initial.shape), evaluate

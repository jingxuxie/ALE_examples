import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csr_matrix

from .io import coefficient


def propagate_lindblad(case, initial, options, jumps=None, specifications=None):
    dimension = len(case['H0'])
    multiple = initial.ndim == 3
    initial = initial if multiple else initial[:, :, None]
    count = initial.shape[-1]
    times = case['times']
    static = csr_matrix(case['H0'])
    controls = [csr_matrix(operator) for operator in case['h_ops']]
    jumps = case['c_ops'] if jumps is None else jumps
    specifications = case['c_coeffs'] if specifications is None else specifications
    sparse_jumps = [csr_matrix(operator) for operator in jumps]
    grams = [operator.getH() @ operator for operator in sparse_jumps]

    def left(operator, density):
        return operator.dot(density.reshape(dimension, -1)).reshape(dimension, dimension, count)

    def right(operator, density):
        return operator.T.dot(density.transpose(1, 0, 2).reshape(dimension, -1)).reshape(dimension, dimension, count).transpose(1, 0, 2)

    controls_all = list(case['h_coeffs']) + list(specifications)
    boundaries = sorted(set([times[0], times[-1]] + [edge for item in controls_all
                         if item['kind'] == 'steps' for edge in item['edges'] if times[0] < edge < times[-1]]))
    maximum_step = (times[-1] - times[0]) / 24
    for specification in controls_all:
        if specification['kind'] == 'gaussian':
            maximum_step = min(maximum_step, specification['width'] / 2)
    maximum_step = min(maximum_step, options.get('max_step', np.inf))
    states = np.empty((len(times), dimension, dimension, count), dtype=complex)
    vector = initial.ravel().copy()
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        def derivative(time, vector):
            effective_time = np.nextafter(stop, start) if time >= stop else time
            density = vector.reshape(dimension, dimension, count)
            result = -1j * (left(static, density) - right(static, density))
            for operator, specification in zip(controls, case['h_coeffs']):
                result += -1j * coefficient(specification, effective_time) * (left(operator, density) - right(operator, density))
            for operator, gram, specification in zip(sparse_jumps, grams, specifications):
                amplitude = coefficient(specification, effective_time)
                result += abs(amplitude) ** 2 * (right(operator.getH(), left(operator, density)) - (left(gram, density) + right(gram, density)) / 2)
            return result.ravel()

        solution = solve_ivp(derivative, (start, stop), vector, method='DOP853', dense_output=True,
                             rtol=options['rtol'], atol=options['atol'], max_step=maximum_step)
        if not solution.success:
            raise RuntimeError(solution.message)
        selected = (times >= start) & (times <= stop)
        states[selected] = solution.sol(times[selected]).T.reshape(-1, dimension, dimension, count)
        vector = solution.y[:, -1]
    return states if multiple else states[:, :, :, 0]

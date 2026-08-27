import numpy as np
from scipy.integrate import solve_ivp

from .baths import spectrum
from .io import coefficient, hamiltonian


def local_operators(case):
    if case['physics'] == 'lindblad':
        return list(case['c_ops']), case['c_coeffs']
    energy_scale = max(float(np.ptp(np.linalg.eigvalsh(case['H0']))), 1e-6)
    operators = [np.sqrt(float(spectrum(bath, energy_scale))) * operator
                 for bath, operator in zip(case['baths'], case['a_ops'])]
    return operators, [{'kind': 'constant'} for operator in operators]


def propagate(case, initial, options):
    dimension = len(case['H0'])
    jumps, coefficients = local_operators(case)
    times = case['times']

    def derivative(time, vector):
        density = vector.reshape(dimension, dimension)
        hamiltonian_value = hamiltonian(case, time)
        result = -1j * (hamiltonian_value @ density - density @ hamiltonian_value)
        for jump, specification in zip(jumps, coefficients):
            scale = float(abs(coefficient(specification, time)))
            gram = jump.conj().T @ jump
            result += scale * (jump @ density @ jump.conj().T - (gram @ density + density @ gram) / 2)
        return result.ravel()

    solution = solve_ivp(derivative, (times[0], times[-1]), initial.ravel(),
                         t_eval=times, rtol=options['rtol'], atol=options['atol'])
    if not solution.success:
        raise RuntimeError(solution.message)
    return solution.y.T.reshape(-1, dimension, dimension)

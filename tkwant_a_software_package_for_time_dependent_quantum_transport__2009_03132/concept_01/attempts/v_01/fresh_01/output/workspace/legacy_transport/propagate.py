import numpy as np
from .protocols import perturbation
from .observables import measure


def evolve(case, hamiltonian, energies, initial, entries, absorb, config):
    wavefunctions = initial.copy()
    time = 0.0
    densities, currents = [], []
    def rhs(clock, state):
        return -1j * (hamiltonian @ state + perturbation(clock, entries, len(state)) @ state) - absorb[:, None] * state
    for target in case['times']:
        while time < target - 1e-12:
            step = min(config['step'], target - time)
            first = rhs(time, wavefunctions)
            second = rhs(time + step / 2, wavefunctions + step / 2 * first)
            third = rhs(time + step / 2, wavefunctions + step / 2 * second)
            fourth = rhs(time + step, wavefunctions + step * third)
            wavefunctions += step / 6 * (first + 2 * second + 2 * third + fourth)
            time += step
        dynamic = hamiltonian + perturbation(target, entries, hamiltonian.shape[0])
        density, current = measure(case, dynamic, wavefunctions)
        densities.append(density)
        currents.append(current)
    return np.asarray(densities), np.asarray(currents)

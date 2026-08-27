import numpy as np
from .protocols import signal, perturbation
from .observables import measure


def evolve(case, hamiltonian, energies, initial, entries, absorb, config):
    deviation = np.zeros_like(initial)
    time = 0.0
    densities, currents = [], []
    def rhs(clock, state):
        output = hamiltonian @ state
        phases = np.exp(-1j * energies * clock)
        for row, column, base, kind, spec in entries:
            amplitude = signal(clock, spec)
            value = base * (np.exp(-1j * amplitude) - 1) if kind == 'phase' else base * amplitude
            output[row] += value * (state[column] + initial[column] * phases)
            if row != column:
                output[column] += value.conjugate() * (state[row] + initial[row] * phases)
        output *= -1j
        if np.any(absorb):
            output -= absorb[:, None] * state
        return output
    for target in case['times']:
        while time < target - 1e-12:
            step = min(config['step'], target - time)
            first = rhs(time, deviation)
            second = rhs(time + step / 2, deviation + step / 2 * first)
            third = rhs(time + step / 2, deviation + step / 2 * second)
            fourth = rhs(time + step, deviation + step * third)
            deviation += step / 6 * (first + 2 * second + 2 * third + fourth)
            time += step
        dynamic = hamiltonian + perturbation(target, entries, hamiltonian.shape[0])
        state = initial * np.exp(-1j * energies * target) + deviation
        density, current = measure(case, dynamic, state)
        densities.append(density)
        currents.append(current)
    return np.asarray(densities), np.asarray(currents)

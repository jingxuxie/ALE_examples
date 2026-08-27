import itertools
import math

import numpy as np


def half_states(momenta, frequencies, cutoff):
    occupations = np.zeros(len(momenta), dtype=np.int16)
    rows = []

    def visit(index, energy, momentum):
        if index == len(momenta):
            rows.append((momentum, energy, occupations.copy()))
            return
        maximum = int((cutoff - energy + 1e-10) / frequencies[index])
        for number in range(maximum + 1):
            occupations[index] = number
            visit(index + 1, energy + number * frequencies[index],
                  momentum + number * momenta[index])

    visit(0, 0.0, 0)
    groups = {}
    for momentum, energy, state in rows:
        groups.setdefault(momentum, []).append((energy, state))
    for group in groups.values():
        group.sort(key=lambda item: item[0])
    return groups


def enumerate_basis(length, mass, cutoff, boundary, momentum, parity):
    minimum = 1 if boundary == 'antiperiodic' else 2
    maximum = int(math.floor(length * math.sqrt(max(cutoff**2 - mass**2, 0)) / math.pi))
    positive = np.arange(minimum, maximum + 1, 2, dtype=np.int16)
    frequencies = np.sqrt(mass**2 + (math.pi * positive / length)**2)
    groups = half_states(positive, frequencies, cutoff)
    modes = np.concatenate((-positive[::-1], [0] if minimum == 2 else [], positive))
    all_frequencies = np.sqrt(mass**2 + (math.pi * modes / length)**2)
    states = []
    energies = []
    for right_momentum, right_states in groups.items():
        left_groups = ([(right_momentum - momentum, groups.get(right_momentum - momentum, []))]
                       if momentum is not None else groups.items())
        for left_momentum, left_states in left_groups:
            for right_energy, right_state in right_states:
                for left_energy, left_state in left_states:
                    remaining = cutoff - right_energy - left_energy
                    if remaining < -1e-9:
                        break
                    maximum_zero = int((remaining + 1e-9) / mass) if minimum == 2 else 0
                    for number in range(maximum_zero + 1):
                        count = int(right_state.sum() + left_state.sum()) + number
                        if parity is not None and count % 2 != parity:
                            continue
                        middle = [number] if minimum == 2 else []
                        states.append(np.concatenate((left_state[::-1], middle, right_state)))
                        energies.append(right_energy + left_energy + number * mass)
    order = np.argsort(energies, kind='stable')
    return (modes, all_frequencies, np.asarray(states, dtype=np.int16)[order],
            np.asarray(energies)[order])

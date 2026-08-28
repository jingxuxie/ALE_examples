import numpy as np
from numba import njit


def initialize(case):
    shape = tuple(case['shape'])
    grid = np.indices(shape)
    count = int(np.prod(shape))
    material = np.asarray((grid.sum(axis=0) % len(case['materials'])).ravel(), dtype=np.int64)
    lattice = np.arange(count).reshape(shape)
    neighbors = np.stack([np.roll(lattice, direction, axis=axis).ravel()
                          for axis in range(3) for direction in (-1, 1)], axis=1)
    random = np.random.default_rng(case['initial_seed'])
    spins = random.normal(size=(count, 3)) * case['disorder']
    for index, values in enumerate(case['materials']):
        spins[material == index] += np.asarray(values['initial_direction'])
    if case.get('twist', 0):
        angle = case['twist'] * grid[0].ravel() / shape[0]
        original = spins.copy()
        spins[:, 0] = np.cos(angle) * original[:, 0] + np.sin(angle) * original[:, 2]
        spins[:, 2] = -np.sin(angle) * original[:, 0] + np.cos(angle) * original[:, 2]
    spins /= np.linalg.norm(spins, axis=1)[:, None]
    parameters = np.array([[values[key] for key in ('mu', 'K', 'A', 'omega0', 'Gamma', 'T')]
                           for values in case['materials']])
    return spins, material, np.ascontiguousarray(neighbors), parameters


@njit(cache=True)
def effective_field(spins, material, neighbors, parameters, exchange, applied):
    result = np.empty_like(spins)
    for atom in range(len(spins)):
        species = material[atom]
        for component in range(3):
            value = applied[component]
            for neighbor in neighbors[atom]:
                value += exchange[species, material[neighbor]] * spins[neighbor, component] / parameters[species, 0]
            result[atom, component] = value
        result[atom, 2] += 2 * parameters[species, 1] * spins[atom, 2] / parameters[species, 0]
    return result


@njit(cache=True)
def classical_integrate(spins, material, neighbors, parameters, exchange, applied, dt, steps, sample_steps):
    trace = np.zeros((len(sample_steps), len(parameters), 3))
    snapshot = 0
    for step in range(steps + 1):
        if snapshot < len(sample_steps) and step == sample_steps[snapshot]:
            for species in range(len(parameters)):
                count = 0
                for atom in range(len(spins)):
                    if material[atom] == species:
                        count += 1
                        for component in range(3):
                            trace[snapshot, species, component] += spins[atom, component]
                trace[snapshot, species] /= count
            snapshot += 1
        if step == steps:
            break
        field = effective_field(spins, material, neighbors, parameters, exchange, applied)
        for atom in range(len(spins)):
            species = material[atom]
            damping = parameters[species, 2] * parameters[species, 4] / parameters[species, 3] ** 4
            precession = np.cross(spins[atom], field[atom])
            change = precession - damping * np.cross(spins[atom], precession)
            spins[atom] += dt * change
            spins[atom] /= np.sqrt(np.sum(spins[atom] ** 2))
    return spins, trace

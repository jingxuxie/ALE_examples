import itertools
import math
from functools import lru_cache

import numpy as np
from scipy.linalg import eigh


FAMILIES = ("local", "collective", "frustrated", "bridge", "density", "mixed")
NVIRTUAL = 8
NPAIRS = 3


@lru_cache(maxsize=None)
def structure(nsites=11, npairs=3):
    configurations = list(itertools.combinations(range(nsites), npairs))
    positions = {configuration: index for index, configuration in enumerate(configurations)}
    occupations = np.zeros((len(configurations), nsites), dtype=float)
    masks = np.zeros(len(configurations), dtype=np.int64)
    rows, columns, sources, targets = [], [], [], []
    for index, configuration in enumerate(configurations):
        occupations[index, list(configuration)] = 1.0
        masks[index] = sum(1 << (orbital - npairs) for orbital in configuration if orbital >= npairs)
        for source in configuration:
            for target in range(nsites):
                if target not in configuration:
                    child = tuple(sorted(set(configuration) - {source} | {target}))
                    rows.append(index)
                    columns.append(positions[child])
                    sources.append(source)
                    targets.append(target)
    return occupations, masks, tuple(np.asarray(values) for values in (rows, columns, sources, targets))


def hamiltonian(model):
    orbital_energy = np.asarray(model["orbital_energy"], dtype=float)
    hopping = np.asarray(model["hopping"], dtype=float)
    density = np.asarray(model["density"], dtype=float)
    occupations, masks, edges = structure(len(orbital_energy), NPAIRS)
    diagonal = occupations @ orbital_energy + 0.5 * np.sum((occupations @ density) * occupations, axis=1)
    matrix = np.diag(diagonal)
    rows, columns, sources, targets = edges
    matrix[rows, columns] = hopping[sources, targets]
    return matrix, masks


class CASOracle:
    def __init__(self, model):
        self.matrix, self.masks = hamiltonian(model)
        self.reference = float(self.matrix[0, 0])
        self.cache = {0: 0.0}

    def energy(self, mask):
        mask = int(mask)
        if mask not in self.cache:
            selected = np.flatnonzero((self.masks & mask) == self.masks)
            restricted = self.matrix[np.ix_(selected, selected)]
            self.cache[mask] = float(eigh(restricted, subset_by_index=(0, 0), eigvals_only=True, check_finite=False)[0] - self.reference)
        return self.cache[mask]

    def spectrum(self):
        eigenvalues, eigenvectors = eigh(self.matrix, subset_by_index=(0, 1), check_finite=False)
        residual = np.linalg.norm(self.matrix @ eigenvectors[:, 0] - eigenvalues[0] * eigenvectors[:, 0])
        return {"energy": float(eigenvalues[0] - self.reference),
                "reference_weight": float(eigenvectors[0, 0] ** 2),
                "gap": float(eigenvalues[1] - eigenvalues[0]),
                "residual": float(residual)}

    def all_energies(self):
        return np.asarray([self.energy(mask) for mask in range(1 << NVIRTUAL)])


def increments(energies):
    values = np.array(energies, dtype=float, copy=True)
    for orbital in range(int(math.log2(len(values)))):
        for mask in range(len(values)):
            if mask & (1 << orbital):
                values[mask] -= values[mask ^ (1 << orbital)]
    return values


def mbesum(energies, order):
    values = increments(energies)
    return math.fsum(float(value) for mask, value in enumerate(values) if mask.bit_count() <= order)


def sample_model(seed, family):
    if family not in FAMILIES:
        raise ValueError("unknown family")
    generator = np.random.default_rng(seed)
    nsites = NPAIRS + NVIRTUAL
    for trial in range(300):
        occupied = np.array([-0.45, -0.22, 0.0])
        virtual = generator.uniform(0.85, 2.4, NVIRTUAL)
        orbital_energy = np.concatenate((occupied, virtual))
        scale = generator.uniform(0.035, 0.12)
        hopping = generator.normal(size=(nsites, nsites))
        hopping = 0.5 * (hopping + hopping.T)
        density = generator.normal(size=(nsites, nsites))
        density = 0.5 * (density + density.T)
        if family == "local":
            location = generator.uniform(0, 1, nsites)
            hopping *= np.exp(-np.abs(location[:, None] - location[None, :]) / 0.25)
            hopping *= scale * 2.1
            density *= 0.08
        elif family == "collective":
            factors = generator.normal(size=(nsites, 2))
            hopping = scale * (factors @ factors.T) / 1.8
            density *= 0.05
        elif family == "frustrated":
            hopping *= scale
            hopping[NPAIRS:, NPAIRS:] *= generator.uniform(2.0, 3.6)
            density *= 0.08
        elif family == "bridge":
            hopping *= 0.025
            ordering = generator.permutation(NVIRTUAL) + NPAIRS
            for left, right in zip(ordering[:-1], ordering[1:]):
                hopping[left, right] = hopping[right, left] = generator.uniform(0.16, 0.38) * generator.choice([-1, 1])
            for occupied_index in range(NPAIRS):
                for target in generator.choice(ordering, 2, replace=False):
                    hopping[occupied_index, target] = hopping[target, occupied_index] = scale * generator.normal()
            density *= 0.06
        elif family == "density":
            hopping *= scale
            density *= generator.uniform(0.16, 0.32)
        else:
            hopping *= scale
            hopping[NPAIRS:, NPAIRS:] *= 2.0
            density *= 0.18
        np.fill_diagonal(hopping, 0)
        np.fill_diagonal(density, 0)
        model = {"family": family, "orbital_energy": orbital_energy.tolist(),
                 "hopping": hopping.tolist(), "density": density.tolist()}
        diagnostics = CASOracle(model).spectrum()
        if diagnostics["reference_weight"] >= 0.94 and diagnostics["gap"] >= 0.35:
            return model
    raise RuntimeError("admissible sampling exhausted")


def initial_observation(model, energies, budget=160):
    return {"event": "start", "nvirtual": NVIRTUAL, "npairs": NPAIRS,
            "family": model["family"], "orbital_energy": model["orbital_energy"],
            "budget": budget, "costs": {"3": 1, "4": 4, "5": 16, "6": 64},
            "values": [[mask, float(energies[mask])] for mask in range(1 << NVIRTUAL) if mask.bit_count() <= 2]}

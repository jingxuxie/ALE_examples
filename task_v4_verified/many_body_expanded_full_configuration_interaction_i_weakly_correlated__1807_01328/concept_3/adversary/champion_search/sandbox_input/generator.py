"""Public synthetic distribution and exact small seniority-zero calculations."""

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations

import numpy as np
from scipy.linalg import eigh


FAMILIES = (
    "coherent", "repulsive", "screened", "frustrated", "mixed_range", "bottleneck"
)
MAX_OCCUPIED = 3
MAX_VIRTUAL = 9
MAX_ORBITALS = 12
PAIR_INDEX = np.asarray(list(combinations(range(MAX_VIRTUAL), 2)), dtype=np.int16)
TRIPLE_INDEX = np.asarray(list(combinations(range(MAX_VIRTUAL), 3)), dtype=np.int16)
EDGE_BOUND = 0.28


@dataclass
class Hamiltonian:
    n_pairs: int
    n_virtual: int
    family: int
    onsite: np.ndarray
    density: np.ndarray
    hopping: np.ndarray
    occupied_profile: np.ndarray
    positions: np.ndarray
    groups: np.ndarray


@lru_cache(maxsize=None)
def basis(n_orbitals, n_pairs):
    states = np.asarray(list(combinations(range(n_orbitals), n_pairs)), dtype=int)
    occupancy = np.zeros((len(states), n_orbitals), dtype=float)
    occupancy[np.arange(len(states))[:, None], states] = 1.0
    lookup = {tuple(state): index for index, state in enumerate(states)}
    rows, columns, sources, destinations = [], [], [], []
    for row, state in enumerate(states):
        occupied = set(state)
        for source in state:
            for destination in range(n_orbitals):
                if destination in occupied:
                    continue
                moved = tuple(sorted((occupied - {source}) | {destination}))
                column = lookup[moved]
                if row < column:
                    rows.append(row)
                    columns.append(column)
                    sources.append(source)
                    destinations.append(destination)
    return occupancy, tuple(np.asarray(values, dtype=int) for values in
                            (rows, columns, sources, destinations))


def matrix(model, virtual_subset=None):
    if virtual_subset is None:
        virtual_subset = tuple(range(model.n_virtual))
    active = np.asarray(list(range(model.n_pairs)) +
                        [model.n_pairs + value for value in virtual_subset])
    occupancy, edges = basis(len(active), model.n_pairs)
    onsite = model.onsite[active]
    density = model.density[np.ix_(active, active)]
    diagonal = occupancy @ onsite + 0.5 * np.sum((occupancy @ density) * occupancy, axis=1)
    result = np.diag(diagonal)
    rows, columns, sources, destinations = edges
    transfers = model.hopping[active[sources], active[destinations]]
    result[rows, columns] = transfers
    result[columns, rows] = transfers
    return result


def ground(model, virtual_subset=None, vectors=False):
    hamiltonian = matrix(model, virtual_subset)
    if vectors:
        energies, eigenvectors = eigh(hamiltonian, subset_by_index=(0, 0),
                                     check_finite=False, driver="evr")
        vector = eigenvectors[:, 0]
        residual = np.linalg.norm(hamiltonian @ vector - energies[0] * vector)
        return float(energies[0]), float(vector[0] ** 2), float(residual)
    return float(eigh(hamiltonian, subset_by_index=(0, 0), eigvals_only=True,
                      check_finite=False, driver="evr")[0])


def sample_hamiltonian(rng, n_pairs=None, n_virtual=None, family=None):
    n_pairs = int(rng.integers(2, 4) if n_pairs is None else n_pairs)
    n_virtual = int(rng.integers(6, 10) if n_virtual is None else n_virtual)
    family = int(rng.integers(len(FAMILIES)) if family is None else family)
    if n_pairs not in (2, 3) or not 6 <= n_virtual <= 9 or not 0 <= family < 6:
        raise ValueError("Unsupported size or family")
    size = n_pairs + n_virtual
    occupied = np.sort(rng.uniform(-0.35, -0.08, size=n_pairs))
    energy_scale = rng.uniform(0.85, 1.35)
    virtual = np.sort(rng.uniform(0.85, 1.8, size=n_virtual)) * energy_scale
    onsite = np.concatenate((occupied, virtual))
    density = rng.uniform(0.0, 0.055, size=(size, size))
    density = (density + density.T) / 2.0
    np.fill_diagonal(density, 0.0)
    profile = rng.uniform(0.65, 1.35, size=n_pairs)
    profile /= np.linalg.norm(profile)
    positions = np.sort(rng.uniform(0.0, 1.0, size=n_virtual))
    groups = (positions > np.median(positions)).astype(np.int8)
    amplitude = rng.uniform(0.105, 0.245)
    source_amplitudes = np.clip(amplitude * rng.lognormal(0.0, 0.18, n_virtual), 0.07, 0.30)
    hopping = np.zeros((size, size))
    hopping[:n_pairs, n_pairs:] = -profile[:, None] * source_amplitudes[None, :]
    hopping[n_pairs:, :n_pairs] = hopping[:n_pairs, n_pairs:].T
    edge_scale = rng.uniform(0.055, 0.15)
    range_scale = rng.uniform(0.20, 0.65)
    for first, second in combinations(range(n_virtual), 2):
        distance = abs(positions[first] - positions[second])
        same_group = groups[first] == groups[second]
        sign = -1.0
        envelope = 1.0
        if family == 1:
            sign = 1.0
        elif family == 2:
            envelope = 0.25 + 1.10 * np.exp(-distance / range_scale)
        elif family == 3:
            sign = -1.0 if same_group else 1.0
            envelope = 1.0 if same_group else 0.75
        elif family == 4:
            sign = -1.0 if distance < 0.35 else 1.0
            envelope = 0.45 + np.exp(-distance / range_scale)
        elif family == 5:
            sign = -1.0 if same_group else 1.0
            envelope = 1.35 if same_group else 0.25
        magnitude = np.clip(edge_scale * envelope * rng.lognormal(0.0, 0.15), 0.012, EDGE_BOUND)
        hopping[n_pairs + first, n_pairs + second] = sign * magnitude
        hopping[n_pairs + second, n_pairs + first] = sign * magnitude
    permutation = rng.permutation(n_virtual)
    orbital_order = np.concatenate((np.arange(n_pairs), n_pairs + permutation))
    return Hamiltonian(n_pairs, n_virtual, family, onsite[orbital_order],
                       density[np.ix_(orbital_order, orbital_order)],
                       hopping[np.ix_(orbital_order, orbital_order)], profile,
                       positions[permutation], groups[permutation])


def low_order_features(model):
    reference = ground(model, ())
    singleton = np.zeros(MAX_VIRTUAL)
    pair_energy = np.zeros(len(PAIR_INDEX))
    triple_energy = np.zeros(len(TRIPLE_INDEX))
    pair_increment = np.zeros_like(pair_energy)
    triple_increment = np.zeros_like(triple_energy)
    pair_lookup = {}
    for virtual in range(model.n_virtual):
        singleton[virtual] = ground(model, (virtual,)) - reference
    for index, (first, second) in enumerate(PAIR_INDEX):
        if second >= model.n_virtual:
            continue
        pair_energy[index] = ground(model, (int(first), int(second))) - reference
        pair_increment[index] = pair_energy[index] - singleton[first] - singleton[second]
        pair_lookup[(first, second)] = pair_increment[index]
    for index, triple in enumerate(TRIPLE_INDEX):
        if triple[-1] >= model.n_virtual:
            continue
        triple_energy[index] = ground(model, tuple(int(value) for value in triple)) - reference
        triple_increment[index] = (triple_energy[index] - singleton[triple].sum() -
                                   sum(pair_lookup[pair] for pair in combinations(triple, 2)))
    onsite = np.zeros(MAX_ORBITALS)
    onsite[:len(model.onsite)] = model.onsite
    density = np.zeros((MAX_ORBITALS, MAX_ORBITALS))
    density[:len(model.onsite), :len(model.onsite)] = model.density
    profile = np.zeros(MAX_OCCUPIED)
    profile[:model.n_pairs] = model.occupied_profile
    positions = np.zeros(MAX_VIRTUAL)
    positions[:model.n_virtual] = model.positions
    groups = np.zeros(MAX_VIRTUAL, dtype=np.int8)
    groups[:model.n_virtual] = model.groups
    pair_sign = np.zeros(len(PAIR_INDEX), dtype=np.int8)
    for index, (first, second) in enumerate(PAIR_INDEX):
        if second < model.n_virtual:
            pair_sign[index] = np.sign(model.hopping[model.n_pairs + first, model.n_pairs + second])
    gaps = np.zeros((MAX_OCCUPIED, MAX_VIRTUAL))
    for occupied in range(model.n_pairs):
        spectators = [other for other in range(model.n_pairs) if other != occupied]
        for virtual in range(model.n_virtual):
            destination = model.n_pairs + virtual
            gaps[occupied, virtual] = (model.onsite[destination] - model.onsite[occupied] +
                                      sum(model.density[destination, other] -
                                          model.density[occupied, other] for other in spectators))
    return {
        "n_pairs": np.int8(model.n_pairs), "n_virtual": np.int8(model.n_virtual),
        "family": np.int8(model.family), "onsite": onsite, "density": density,
        "occupied_profile": profile, "positions": positions, "groups": groups,
        "pair_sign": pair_sign, "diagonal_gaps": gaps,
        "reference_energy": np.float64(reference), "cas1": singleton,
        "cas2": pair_energy, "cas3": triple_energy, "inc1": singleton.copy(),
        "inc2": pair_increment, "inc3": triple_increment,
        "truncated_correlation": np.float64(singleton.sum() + pair_increment.sum() + triple_increment.sum()),
    }


def label(model, features=None):
    features = low_order_features(model) if features is None else features
    energy, reference_weight, residual = ground(model, vectors=True)
    correlation = energy - features["reference_energy"]
    return {"tail": float(correlation - features["truncated_correlation"]),
            "correlation": float(correlation), "reference_weight": reference_weight,
            "residual": residual}


def accepted_sample(rng, n_pairs, n_virtual, family):
    for rejection_count in range(10000):
        model = sample_hamiltonian(rng, n_pairs, n_virtual, family)
        features = low_order_features(model)
        truth = label(model, features)
        if (truth["reference_weight"] >= 0.85 and abs(truth["tail"]) >= 1.5e-4 and
                np.min(features["diagonal_gaps"][:n_pairs, :n_virtual]) >= 0.80):
            return model, features, truth, rejection_count
    raise RuntimeError("Rejection sampler exhausted")


def full_order_sums(model):
    reference = ground(model, ())
    increments = {0: 0.0}
    sums = np.zeros(model.n_virtual + 1)
    for order in range(1, model.n_virtual + 1):
        for subset in combinations(range(model.n_virtual), order):
            mask = sum(1 << virtual for virtual in subset)
            increment = ground(model, subset) - reference
            submask = (mask - 1) & mask
            while submask:
                increment -= increments[submask]
                submask = (submask - 1) & mask
            increments[mask] = increment
            sums[order] += increment
    return sums

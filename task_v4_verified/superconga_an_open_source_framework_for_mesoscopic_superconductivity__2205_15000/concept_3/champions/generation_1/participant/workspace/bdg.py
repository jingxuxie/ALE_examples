import itertools
import math

import numpy as np
from scipy.linalg import eigh, solve


SPEC = {
    "version": "ldos-tomography-v1",
    "size": 8,
    "hopping": 1.0,
    "chemical_potential": -0.7,
    "gap": 0.55,
    "core_radius": 1.15,
    "broadening": 0.065,
    "energies": [round(-2.4 + 0.12 * index, 8) for index in range(41)],
    "impurity_sites": [8 * row + column for row in range(1, 7) for column in range(1, 7)],
    "impurity_count": [4, 7],
    "strength_abs": [0.55, 1.6],
    "vortex_centers": [[column, row] for row in (1.5, 3.5, 5.5) for column in (1.5, 3.5, 5.5)],
    "vortex_count": [0, 1, 2],
    "families": ["dispersed", "crowded", "clustered"],
    "query_budget": 56,
    "noise_std": 0.0,
    "cpu_seconds": 90,
    "wall_seconds": 120,
    "memory_mb": 2048,
}


def integer(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(name + " must be an integer")
    if not lower <= value <= upper:
        raise ValueError(name + " out of range")
    return int(value)


def real(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(name + " must be a finite real number")
    if not math.isfinite(float(value)):
        raise ValueError(name + " must be finite")
    return float(value)


def validate_scene(scene, prior=True):
    if not isinstance(scene, dict) or set(scene) != {"impurities", "vortices"}:
        raise ValueError("scene requires exactly impurities and vortices")
    impurities = scene["impurities"]
    vortices = scene["vortices"]
    if not isinstance(impurities, list) or not isinstance(vortices, list):
        raise ValueError("impurities and vortices must be lists")
    lower, upper = SPEC["impurity_count"]
    if (prior and not lower <= len(impurities) <= upper) or len(impurities) > 36:
        raise ValueError("invalid impurity count")
    if len(vortices) > 2:
        raise ValueError("at most two vortices")
    sites = set()
    cleaned = []
    for impurity in impurities:
        if not isinstance(impurity, dict) or set(impurity) != {"site", "strength"}:
            raise ValueError("impurity requires site and strength")
        site = integer(impurity["site"], "site", 0, 63)
        strength = real(impurity["strength"], "strength")
        if site not in SPEC["impurity_sites"] or site in sites:
            raise ValueError("invalid or duplicate impurity site")
        if prior and not SPEC["strength_abs"][0] <= abs(strength) <= SPEC["strength_abs"][1]:
            raise ValueError("strength outside prior")
        sites.add(site)
        cleaned.append({"site": site, "strength": strength})
    vortex_ids = [integer(value, "vortex", 0, 8) for value in vortices]
    if len(set(vortex_ids)) != len(vortex_ids):
        raise ValueError("duplicate vortex")
    return {"impurities": sorted(cleaned, key=lambda item: item["site"]), "vortices": sorted(vortex_ids)}


def validate_action(action):
    if not isinstance(action, dict) or set(action) != {"type", "site", "energy_index"}:
        raise ValueError("query requires exactly type, site, energy_index")
    if action["type"] != "query":
        raise ValueError("expected query")
    site = integer(action["site"], "site", 0, 63)
    energy_index = integer(action["energy_index"], "energy_index", 0, 40)
    return site, energy_index


def sectors():
    return [list(group) for count in (0, 1, 2) for group in itertools.combinations(range(9), count)]


def draw_scene(seed, family):
    if family not in SPEC["families"]:
        raise ValueError("unknown family")
    generator = np.random.default_rng(seed)
    counts = {"dispersed": (4, 5), "crowded": (6, 7), "clustered": (5, 6, 7)}
    count = int(generator.choice(counts[family]))
    candidates = SPEC["impurity_sites"]
    if family == "clustered":
        anchor_column, anchor_row = generator.integers(1, 4, size=2)
        candidates = [8 * row + column for row in range(anchor_row, anchor_row + 4)
                      for column in range(anchor_column, anchor_column + 4)]
    sites = generator.choice(candidates, count, replace=False)
    strengths = generator.uniform(*SPEC["strength_abs"], count) * generator.choice((-1, 1), count)
    vortex_count = int(generator.integers(0, 3))
    vortices = generator.choice(9, vortex_count, replace=False).tolist()
    return validate_scene({"impurities": [{"site": int(site), "strength": float(strength)}
                                         for site, strength in zip(sites, strengths)], "vortices": vortices})


def potential_of(scene):
    scene = validate_scene(scene, prior=False)
    potential = np.zeros(64)
    for impurity in scene["impurities"]:
        potential[impurity["site"]] = impurity["strength"]
    return potential


def pairing(vortices, gap=None, phase=0.0, winding=1):
    validate_scene({"impurities": [], "vortices": vortices}, prior=False)
    gap = SPEC["gap"] if gap is None else real(gap, "gap")
    if gap < 0:
        raise ValueError("gap must be nonnegative")
    if winding not in (-1, 1):
        raise ValueError("winding must be +1 or -1")
    rows, columns = np.indices((8, 8))
    amplitude = np.full((8, 8), gap, dtype=float)
    angle = np.full((8, 8), real(phase, "phase"), dtype=float)
    for vortex in vortices:
        center_column, center_row = SPEC["vortex_centers"][vortex]
        displacement_column = columns - center_column
        displacement_row = rows - center_row
        distance = np.hypot(displacement_column, displacement_row)
        amplitude *= np.tanh(distance / SPEC["core_radius"])
        angle += winding * np.arctan2(displacement_row, displacement_column)
    return (amplitude * np.exp(1j * angle)).ravel()


def hamiltonian(potential, vortices, gap=None, phase=0.0, winding=1):
    potential = np.asarray(potential)
    if potential.shape != (64,) or np.iscomplexobj(potential) or not np.all(np.isfinite(potential)):
        raise ValueError("potential must be a finite real length-64 array")
    normal = np.diag(potential.astype(float) - SPEC["chemical_potential"])
    for site in range(64):
        row, column = divmod(site, 8)
        for neighbor in ([site + 1] if column < 7 else []) + ([site + 8] if row < 7 else []):
            normal[site, neighbor] = normal[neighbor, site] = -SPEC["hopping"]
    pair = np.diag(pairing(vortices, gap=gap, phase=phase, winding=winding))
    return np.block([[normal, pair], [pair.conj().T, -normal.conj()]])


def _query_arrays(actions):
    if not isinstance(actions, (list, tuple)) or not actions:
        raise ValueError("actions must be a nonempty list")
    validated = [validate_action(action) for action in actions]
    return np.asarray([item[0] for item in validated]), np.asarray([SPEC["energies"][item[1]] for item in validated])


def predict_potential(potential, vortices, actions, jacobian=False):
    sites, energies = _query_arrays(actions)
    eigenvalues, eigenvectors = eigh(hamiltonian(potential, vortices), check_finite=False, driver="evr")
    inverse = 1.0 / (energies[:, None] + 1j * SPEC["broadening"] - eigenvalues)
    electron = eigenvectors[sites]
    values = -np.imag(np.sum(abs(electron) ** 2 * inverse, axis=1)) / np.pi
    if not jacobian:
        return values
    impurity_sites = np.asarray(SPEC["impurity_sites"])
    columns = np.concatenate((impurity_sites, impurity_sites + 64))
    forward = (electron * inverse) @ eigenvectors[columns].conj().T
    backward = (electron.conj() * inverse) @ eigenvectors[columns].T
    products = forward * backward
    gradient = -np.imag(products[:, :36] - products[:, 36:]) / np.pi
    return values, gradient


def simulate(scene, actions):
    scene = validate_scene(scene, prior=False)
    return predict_potential(potential_of(scene), scene["vortices"], actions)


def ldos_table(scene):
    scene = validate_scene(scene, prior=False)
    eigenvalues, eigenvectors = eigh(hamiltonian(potential_of(scene), scene["vortices"]), check_finite=False)
    energy = np.asarray(SPEC["energies"])
    lorentzian = SPEC["broadening"] / (np.pi * ((energy[None, :] - eigenvalues[:, None]) ** 2 + SPEC["broadening"] ** 2))
    return abs(eigenvectors[:64]) ** 2 @ lorentzian


def resolvent_ldos(scene, actions):
    sites, energies = _query_arrays(actions)
    matrix = hamiltonian(potential_of(scene), scene["vortices"])
    identity = np.eye(128, dtype=complex)
    values = []
    for site, energy in zip(sites, energies):
        column = solve((energy + 1j * SPEC["broadening"]) * identity - matrix, identity[:, site], check_finite=False)
        values.append(-column[site].imag / np.pi)
    return np.asarray(values)


def uniform_actions(count=56, seed=1701):
    count = integer(count, "count", 1, 2624)
    generator = np.random.default_rng(seed)
    indices = generator.choice(64 * 41, count, replace=False)
    return [{"type": "query", "site": int(index // 41), "energy_index": int(index % 41)} for index in indices]

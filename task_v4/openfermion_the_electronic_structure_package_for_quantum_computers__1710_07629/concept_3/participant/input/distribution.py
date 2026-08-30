"""Public generative law. Seeds and row numbers are not model inputs."""

import numpy as np


FAMILIES = ("dimerized_ring", "open_ladder", "triangular_ladder", "periodic_ladder")


def draw_instance(rng, family, n_sites=8):
    interaction = rng.uniform(2.0, 8.0)
    disorder = rng.uniform(0.0, 2.5)
    dimerization = rng.uniform(0.0, 0.5)
    transverse = rng.uniform(0.6, 1.4)
    frustration = rng.uniform(0.15, 0.65)
    heterogeneity = rng.uniform(0.0, 0.2)
    phase = rng.uniform(0.0, 2.0 * np.pi)
    hopping = np.zeros((n_sites, n_sites), dtype=np.float64)

    def bond(first, second, strength):
        value = strength * rng.uniform(0.9, 1.1)
        hopping[first, second] = value
        hopping[second, first] = value

    if family == 0:
        for site in range(n_sites):
            bond(site, (site + 1) % n_sites,
                 1.0 + dimerization * (-1) ** site)
    else:
        length = n_sites // 2
        for leg in range(2):
            for column in range(length - 1):
                bond(leg * length + column, leg * length + column + 1,
                     1.0 + dimerization * (-1) ** column)
            if family == 3:
                bond(leg * length + length - 1, leg * length,
                     1.0 + dimerization * (-1) ** (length - 1))
        for column in range(length):
            bond(column, length + column, transverse)
        if family == 2:
            for column in range(length - 1):
                bond(column, length + column + 1, frustration)
    positions = np.arange(n_sites)
    potential = disorder * (
        0.6 * np.cos(2.0 * np.pi * positions / n_sites + phase)
        + 0.4 * rng.uniform(-1.0, 1.0, n_sites))
    potential -= potential.mean()
    onsite = interaction * (1.0 + heterogeneity * rng.uniform(-1.0, 1.0, n_sites))
    permutation = rng.permutation(n_sites)
    return (hopping[np.ix_(permutation, permutation)], onsite[permutation],
            potential[permutation], family)


def draw_batch(count_per_family, seed, n_sites=None):
    rng = np.random.default_rng(seed)
    rows = [draw_instance(rng, family, n_sites if n_sites is not None else int(rng.choice([8, 10])))
            for family in range(4) for _ in range(count_per_family)]
    rows = [rows[index] for index in rng.permutation(len(rows))]
    width = n_sites if n_sites is not None else 10
    return {"hopping": np.stack([np.pad(row[0], ((0, width - len(row[0])),
                                                 (0, width - len(row[0])))) for row in rows]),
            "interaction": np.stack([np.pad(row[1], (0, width - len(row[1]))) for row in rows]),
            "potential": np.stack([np.pad(row[2], (0, width - len(row[2]))) for row in rows]),
            "n_sites": np.array([len(row[0]) for row in rows], dtype=np.int64),
            "family": np.array([row[3] for row in rows], dtype=np.int64)}

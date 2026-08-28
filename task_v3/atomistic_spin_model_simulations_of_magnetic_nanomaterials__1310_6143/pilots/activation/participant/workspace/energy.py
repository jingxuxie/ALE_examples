import json
from pathlib import Path

import numpy as np


def load_case(path):
    return json.loads(Path(path).read_text())


def energy_gradient(case, spins):
    spins = np.asarray(spins, dtype=float)
    exchange = np.asarray(case["exchange_meV"])
    anisotropy = np.asarray(case["anisotropy_meV"])
    field = np.asarray(case["field_meV"])
    anisotropy_spins = np.einsum("nij,nj->ni", anisotropy, spins)
    energy = -np.sum(exchange * np.sum(spins[:-1] * spins[1:], axis=1))
    energy -= np.sum(spins * anisotropy_spins) + np.sum(spins * field)
    gradient = -2 * anisotropy_spins - np.broadcast_to(field, spins.shape).copy()
    gradient[:-1] -= exchange[:, None] * spins[1:]
    gradient[1:] -= exchange[:, None] * spins[:-1]
    return float(energy), gradient


def tangent_gradient(case, spins):
    energy, gradient = energy_gradient(case, spins)
    return energy, gradient - np.sum(gradient * spins, axis=1)[:, None] * spins


def relax(case, initial, max_steps=2000, tolerance=1e-7):
    spins = np.asarray(initial, dtype=float).copy()
    spins /= np.linalg.norm(spins, axis=1)[:, None]
    step = 0.1 / max(1.0, max(case["exchange_meV"]))
    for iteration in range(max_steps):
        energy, gradient = tangent_gradient(case, spins)
        if np.max(np.linalg.norm(gradient, axis=1)) < tolerance:
            break
        accepted = False
        for backtrack in range(20):
            trial = spins - step * gradient
            trial /= np.linalg.norm(trial, axis=1)[:, None]
            if energy_gradient(case, trial)[0] <= energy - 1e-4 * step * np.sum(gradient**2):
                spins = trial
                step = min(step * 1.2, 0.5)
                accepted = True
                break
            step *= 0.5
        if not accepted:
            break
    return spins

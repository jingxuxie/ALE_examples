import ctypes
import itertools
from functools import lru_cache
from pathlib import Path

import numpy as np


POINTER = ctypes.POINTER(ctypes.c_double)
LIBRARY = ctypes.CDLL(str(Path(__file__).resolve().with_name('hubbard.so')))
LIBRARY.ground_energy.argtypes = (
    [ctypes.c_int] * 3 + [POINTER] * 5
    + [ctypes.c_int, ctypes.c_double, POINTER]
)
LIBRARY.ground_energy.restype = ctypes.c_double


def pointer(array):
    return array.ctypes.data_as(POINTER)


@lru_cache(maxsize=16)
def occupations(sites, particles):
    configurations = itertools.combinations(range(sites), particles)
    configurations = sorted(
        configurations,
        key=lambda occupied: sum(1 << site for site in occupied),
    )
    return np.array(configurations)


def predict_instance(hopping, interaction, potential, steps=160, tolerance=1e-8):
    sites = len(interaction)
    half = sites // 2
    hopping = np.ascontiguousarray(hopping, dtype=np.float64)
    interaction = np.ascontiguousarray(interaction, dtype=np.float64)
    potential = np.ascontiguousarray(potential, dtype=np.float64)
    one_body = -hopping + np.diag(
        potential + 0.5 * (interaction - np.mean(interaction))
    )
    _, orbitals = np.linalg.eigh(one_body)
    trials = {
        particles: np.ascontiguousarray(
            np.linalg.det(orbitals[occupations(sites, particles), :particles])
        )
        for particles in range(1, sites)
    }

    def sector_energy(up, down):
        return LIBRARY.ground_energy(
            sites, up, down, pointer(hopping), pointer(interaction),
            pointer(potential), pointer(trials[up]), pointer(trials[down]),
            steps, tolerance, None,
        )

    neutral_energies = [
        sector_energy(half + polarization, half - polarization)
        for polarization in range(half)
    ]
    potential_sum = float(np.sum(potential))
    neutral_energies.append(potential_sum)
    neutral_energy = min(neutral_energies)
    spin_energy = min(neutral_energies[1:])
    added_energies = [
        sector_energy(half + 1 + polarization, half - polarization)
        for polarization in range(half - 1)
    ]
    removed_energies = [
        sector_energy(half + polarization, half - 1 - polarization)
        for polarization in range(half - 1)
    ]
    added_energies.append(potential_sum + np.linalg.eigvalsh(
        -hopping + np.diag(potential + interaction)
    )[0])
    removed_energies.append(potential_sum - np.linalg.eigvalsh(
        -hopping + np.diag(potential)
    )[-1])
    return [
        float(min(added_energies) + min(removed_energies) - 2 * neutral_energy),
        float(spin_energy - neutral_energy),
    ]


def predict(inputs):
    predictions = []
    for index, padded_sites in enumerate(inputs['n_sites']):
        sites = int(padded_sites)
        predictions.append(predict_instance(
            inputs['hopping'][index, :sites, :sites],
            inputs['interaction'][index, :sites],
            inputs['potential'][index, :sites],
        ))
    return predictions

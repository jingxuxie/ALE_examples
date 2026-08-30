import itertools
import json
import math
import os
import stat
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.linalg import eigh


INPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "input"
TARGET = json.loads((INPUT_DIRECTORY / "target.json").read_text())
VIRTUAL_COUNT = TARGET["virtual_count"]
ORBITAL_COUNT = VIRTUAL_COUNT + TARGET["pair_count"]
FULL_MASK = (1 << VIRTUAL_COUNT) - 1
TRIPLE_MASKS = [mask for mask in range(FULL_MASK + 1) if mask.bit_count() == 3]


def unique_object(entries):
    result = {}
    for key, value in entries:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON constant")


def load_witness(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode):
            raise ValueError("witness must be a regular file")
        data = stream.read(TARGET["max_witness_bytes"] + 1)
    if len(data) > TARGET["max_witness_bytes"]:
        raise ValueError("witness exceeds byte limit")
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)


def matrix_field(witness, field, bound):
    value = witness[field]
    if not isinstance(value, list) or len(value) != VIRTUAL_COUNT:
        raise ValueError(field + " must have seven rows")
    for row in value:
        if not isinstance(row, list) or len(row) != VIRTUAL_COUNT:
            raise ValueError(field + " must be 7 by 7")
        if any(type(entry) not in (int, float) for entry in row):
            raise ValueError(field + " entries must be numbers, not booleans")
    matrix = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(matrix)):
        raise ValueError(field + " contains non-finite values")
    if not np.array_equal(matrix, matrix.T):
        raise ValueError(field + " must be exactly symmetric")
    if np.any(np.diag(matrix) != 0.0):
        raise ValueError(field + " diagonal must be zero")
    if np.max(np.abs(matrix)) > bound:
        raise ValueError(field + " exceeds its bound")
    return matrix


def decode_witness(witness):
    if not isinstance(witness, dict) or set(witness) != {"schema_version", "virtual_hopping", "virtual_density"}:
        raise ValueError("witness has missing or extra fields")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise ValueError("schema_version must be the integer 1")
    hopping = np.zeros((ORBITAL_COUNT, ORBITAL_COUNT))
    density = np.array(TARGET["background_density"], dtype=float)
    hopping[:3, 3:] = np.array(TARGET["occupied_virtual_hopping"])
    hopping[3:, :3] = hopping[:3, 3:].T
    hopping[3:, 3:] = matrix_field(witness, "virtual_hopping", TARGET["hopping_bound_eh"])
    density[3:, 3:] = matrix_field(witness, "virtual_density", TARGET["density_bound_eh"])
    return hopping, density


@lru_cache(maxsize=128)
def topology(mask):
    if type(mask) is not int or not 0 <= mask <= FULL_MASK:
        raise ValueError("invalid subset mask")
    orbitals = list(range(3)) + [3 + index for index in range(VIRTUAL_COUNT) if mask & (1 << index)]
    basis = list(itertools.combinations(orbitals, 3))
    occupation = np.zeros((len(basis), ORBITAL_COUNT))
    for position, state in enumerate(basis):
        occupation[position, list(state)] = 1.0
    state_index = {state: index for index, state in enumerate(basis)}
    rows, columns, sources, destinations = [], [], [], []
    for row, state in enumerate(basis):
        for source in state:
            for destination in orbitals:
                if destination not in state:
                    child = tuple(sorted((set(state) - {source}) | {destination}))
                    column = state_index[child]
                    if column < row:
                        rows.append(row)
                        columns.append(column)
                        sources.append(source)
                        destinations.append(destination)
    return occupation, tuple(np.array(entries, dtype=int) for entries in (rows, columns, sources, destinations))


def hamiltonian(mask, hopping, density):
    occupation, (rows, columns, sources, destinations) = topology(mask)
    diagonal = occupation @ np.array(TARGET["pair_energy_eh"])
    diagonal += 0.5 * np.sum((occupation @ density) * occupation, axis=1)
    matrix = np.diag(diagonal)
    matrix[rows, columns] = matrix[columns, rows] = hopping[sources, destinations]
    return matrix


def subset_energy(mask, hopping, density):
    matrix = hamiltonian(mask, hopping, density)
    return float(eigh(matrix, subset_by_index=(0, 0), eigvals_only=True, check_finite=True)[0])


def compute(witness, complete=True):
    hopping, density = decode_witness(witness)
    masks = list(range(FULL_MASK + 1)) if complete else [mask for mask in range(FULL_MASK + 1) if mask.bit_count() <= 3]
    energies = {mask: subset_energy(mask, hopping, density) for mask in masks}
    reference_energy = energies[0]
    increments = {0: 0.0}
    for mask in masks[1:]:
        submask = (mask - 1) & mask
        proper = []
        while submask:
            proper.append(increments[submask])
            submask = (submask - 1) & mask
        increments[mask] = energies[mask] - reference_energy - math.fsum(proper)
    full_matrix = hamiltonian(FULL_MASK, hopping, density)
    values, vectors = eigh(full_matrix, subset_by_index=(0, 1), check_finite=True)
    truncation = reference_energy + math.fsum(value for mask, value in increments.items() if 1 <= mask.bit_count() <= 3)
    signed_tail = float(values[0] - truncation)
    largest_parent = max(abs(increments[mask]) for mask in TRIPLE_MASKS)
    result = {
        "reference_energy_eh": reference_energy,
        "full_energy_eh": float(values[0]),
        "third_order_energy_eh": truncation,
        "signed_tail_eh": signed_tail,
        "tail_eh": abs(signed_tail),
        "max_abs_triple_eh": largest_parent,
        "tail_to_parent_ratio": abs(signed_tail) / max(largest_parent, TARGET["ratio_floor_eh"]),
        "hf_weight": float(vectors[0, 0] ** 2),
        "spectral_gap_eh": float(values[1] - values[0]),
        "diagonal_margin_eh": float(np.min(np.diag(full_matrix)[1:] - full_matrix[0, 0])),
        "eigen_residual_eh": float(np.max(np.abs(full_matrix @ vectors - vectors * values))),
        "subset_energies_eh": {str(mask): value for mask, value in energies.items()},
        "increments_eh": {str(mask): value for mask, value in increments.items()},
        "order_sums_eh": {str(order): math.fsum(value for mask, value in increments.items() if mask.bit_count() == order) for order in range(1, 8 if complete else 4)},
        "order_max_abs_eh": {str(order): max(abs(value) for mask, value in increments.items() if mask.bit_count() == order) for order in range(1, 8 if complete else 4)},
    }
    if complete:
        result["closure_error_eh"] = abs(reference_energy + math.fsum(increments.values()) - values[0])
    return result


def score(metrics):
    numeric = [value for value in metrics.values() if isinstance(value, (int, float))]
    if not all(math.isfinite(value) for value in numeric):
        return dict(valid=False, passed=False, reason="non-finite recomputed diagnostic", core_score=0.0)
    admissibility = {
        "hf_weight": metrics["hf_weight"] >= TARGET["min_hf_weight"],
        "spectral_gap": metrics["spectral_gap_eh"] >= TARGET["min_spectral_gap_eh"],
        "diagonal_margin": metrics["diagonal_margin_eh"] >= TARGET["min_diagonal_margin_eh"],
        "eigen_residual": metrics["eigen_residual_eh"] <= TARGET["numerical_check_eh"],
    }
    valid = all(admissibility.values())
    checks = {
        "all_triples_small": metrics["max_abs_triple_eh"] <= TARGET["parent_threshold_eh"],
        "material_tail": metrics["tail_eh"] >= TARGET["min_tail_eh"],
        "large_ratio": metrics["tail_to_parent_ratio"] >= TARGET["min_tail_to_parent_ratio"],
    }
    factors = [1.0, TARGET["parent_threshold_eh"] / max(metrics["max_abs_triple_eh"], TARGET["ratio_floor_eh"]), metrics["tail_eh"] / TARGET["min_tail_eh"], metrics["tail_to_parent_ratio"] / TARGET["min_tail_to_parent_ratio"]]
    return {
        "valid": valid,
        "passed": valid and all(checks.values()),
        "reason": "witness passes" if valid and all(checks.values()) else ("admissible, target not met" if valid else "inadmissible Hamiltonian"),
        "core_score": min(factors) if valid else 0.0,
        "admissibility": admissibility,
        "witness_checks": checks,
    }

import itertools
import json
import math
import os
import resource
import stat
import sys
import time
from pathlib import Path

import numpy as np


TARGET = json.loads(Path(__file__).with_name("target.json").read_text())


def object_from_pairs(pairs):
    mapping = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError("duplicate key: " + key)
        mapping[key] = value
    return mapping


def invalid_constant(constant):
    raise ValueError("non-finite JSON constant")


def read_candidate(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("witness is not a regular file")
        if metadata.st_size > TARGET["max_witness_bytes"]:
            raise ValueError("witness exceeds byte limit")
        payload = stream.read(TARGET["max_witness_bytes"] + 1)
    if len(payload) > TARGET["max_witness_bytes"]:
        raise ValueError("witness exceeds byte limit")
    witness = json.loads(payload.decode("utf-8"), object_pairs_hook=object_from_pairs, parse_constant=invalid_constant)
    if type(witness) is not dict or set(witness) != {"schema_version", "virtual_hopping", "virtual_density"}:
        raise ValueError("unexpected witness fields")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    matrices = []
    for field, bound in (("virtual_hopping", TARGET["hopping_bound_eh"]), ("virtual_density", TARGET["density_bound_eh"])):
        entries = witness[field]
        if type(entries) is not list or len(entries) != 7:
            raise ValueError(field + ": expected 7 rows")
        for row in entries:
            if type(row) is not list or len(row) != 7:
                raise ValueError(field + ": expected 7 columns")
            for number in row:
                if type(number) not in (float, int) or not math.isfinite(number):
                    raise ValueError(field + ": finite numbers required")
                if abs(number) > bound:
                    raise ValueError(field + ": coefficient out of bounds")
        for row in range(7):
            if entries[row][row] != 0:
                raise ValueError(field + ": diagonal must be zero")
            for column in range(row):
                if entries[row][column] != entries[column][row]:
                    raise ValueError(field + ": exact symmetry required")
        matrices.append(entries)
    return tuple(matrices)


def fermionic_pair_move(pair_state, source, destination):
    spin_state = sum(3 << (2 * orbital) for orbital in range(10) if pair_state & (1 << orbital))
    phase = 1
    operations = ((2 * source, False), (2 * source + 1, False), (2 * destination + 1, True), (2 * destination, True))
    for orbital, create in operations:
        present = bool(spin_state & (1 << orbital))
        if present == create:
            raise ValueError("invalid pair operator action")
        if (spin_state & ((1 << orbital) - 1)).bit_count() % 2:
            phase = -phase
        spin_state ^= 1 << orbital
    return phase


def build_full(virtual_hopping, virtual_density):
    states = [state for state in range(1 << 10) if state.bit_count() == 3]
    matrix = np.zeros((len(states), len(states)))
    occupied = [[orbital for orbital in range(10) if state & (1 << orbital)] for state in states]
    background = TARGET["background_density"]
    for position, orbitals in enumerate(occupied):
        diagonal_terms = [TARGET["pair_energy_eh"][orbital] for orbital in orbitals]
        diagonal_terms += [background[source][destination] if source < 3 else virtual_density[source - 3][destination - 3] for source, destination in itertools.combinations(orbitals, 2)]
        matrix[position, position] = math.fsum(diagonal_terms)
    for row, left_state in enumerate(states):
        for column in range(row):
            right_state = states[column]
            if (left_state ^ right_state).bit_count() != 2:
                continue
            source = (right_state & ~left_state).bit_length() - 1
            destination = (left_state & ~right_state).bit_length() - 1
            lower, upper = sorted((source, destination))
            if upper < 3:
                coefficient = 0.0
            elif lower < 3:
                coefficient = TARGET["occupied_virtual_hopping"][lower][upper - 3]
            else:
                coefficient = virtual_hopping[lower - 3][upper - 3]
            matrix[row, column] = matrix[column, row] = coefficient * fermionic_pair_move(right_state, source, destination)
    return matrix, states


def calculate(virtual_hopping, virtual_density):
    matrix, states = build_full(virtual_hopping, virtual_density)
    values, vectors = np.linalg.eigh(matrix)
    reference_index = states.index(7)
    reference_energy = float(matrix[reference_index, reference_index])
    energies = {}
    for mask in range(128):
        allowed = 7 | (mask << 3)
        indices = [position for position, state in enumerate(states) if state & ~allowed == 0]
        energies[mask] = float(np.linalg.eigvalsh(matrix[np.ix_(indices, indices)])[0])
    increments = {0: 0.0}
    for mask in range(1, 128):
        submask = mask
        summands = []
        while submask:
            sign = -1 if (mask.bit_count() - submask.bit_count()) % 2 else 1
            summands.append(sign * (energies[submask] - reference_energy))
            submask = (submask - 1) & mask
        increments[mask] = math.fsum(summands)
    order_sums = {str(order): math.fsum(value for mask, value in increments.items() if mask.bit_count() == order) for order in range(1, 8)}
    truncation = reference_energy + math.fsum(increments[mask] for mask in range(1, 128) if mask.bit_count() <= 3)
    signed_tail = float(values[0] - truncation)
    triple_maximum = max(abs(increments[mask]) for mask in range(128) if mask.bit_count() == 3)
    discarded_children = 0
    for mask in range(128):
        if mask.bit_count() != 4:
            continue
        parent_maximum = max(abs(increments[mask ^ (1 << index)]) for index in range(7) if mask & (1 << index))
        discarded_children += int(parent_maximum <= TARGET["parent_threshold_eh"])
    monotonicity_error = max(energies[mask | (1 << index)] - energies[mask] for mask in range(128) for index in range(7) if not mask & (1 << index))
    return {
        "reference_energy_eh": reference_energy,
        "full_energy_eh": float(values[0]),
        "third_order_energy_eh": truncation,
        "signed_tail_eh": signed_tail,
        "tail_eh": abs(signed_tail),
        "max_abs_triple_eh": triple_maximum,
        "tail_to_parent_ratio": abs(signed_tail) / max(triple_maximum, TARGET["ratio_floor_eh"]),
        "hf_weight": float(vectors[reference_index, 0] ** 2),
        "spectral_gap_eh": float(values[1] - values[0]),
        "diagonal_margin_eh": min(float(matrix[index, index] - reference_energy) for index in range(len(states)) if index != reference_index),
        "eigen_residual_eh": float(np.max(np.abs(matrix @ vectors[:, :2] - vectors[:, :2] * values[:2]))),
        "closure_error_eh": float(abs(reference_energy + math.fsum(increments.values()) - values[0])),
        "variational_violation_eh": max(0.0, monotonicity_error),
        "full_solver_disagreement_eh": float(abs(energies[127] - values[0])),
        "discarded_quadruples": discarded_children,
        "quadruple_count": 35,
        "order_sums_eh": order_sums,
        "order_max_abs_eh": {str(order): max(abs(value) for mask, value in increments.items() if mask.bit_count() == order) for order in range(1, 8)},
        "subset_energies_eh": {str(mask): value for mask, value in energies.items()},
        "increments_eh": {str(mask): value for mask, value in increments.items()},
    }


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(entry) for entry in value.values())
    if isinstance(value, list):
        return all(finite_tree(entry) for entry in value)
    return isinstance(value, (int, float, np.integer, np.floating)) and math.isfinite(value)


def assess(metrics):
    if not finite_tree(metrics):
        return dict(valid=False, passed=False, core_score=0.0, worst_family_score=None, reason="non-finite recomputed diagnostic")
    numerical_limit = TARGET["numerical_check_eh"]
    admissibility = {
        "hf_weight": metrics["hf_weight"] >= TARGET["min_hf_weight"],
        "spectral_gap": metrics["spectral_gap_eh"] >= TARGET["min_spectral_gap_eh"],
        "diagonal_margin": metrics["diagonal_margin_eh"] >= TARGET["min_diagonal_margin_eh"],
        "eigen_residual": metrics["eigen_residual_eh"] <= numerical_limit,
        "closure": metrics["closure_error_eh"] <= numerical_limit,
        "variational": metrics["variational_violation_eh"] <= numerical_limit,
        "solver_agreement": metrics["full_solver_disagreement_eh"] <= numerical_limit,
    }
    witness_checks = {
        "all_triples_small": metrics["max_abs_triple_eh"] <= TARGET["parent_threshold_eh"],
        "material_tail": metrics["tail_eh"] >= TARGET["min_tail_eh"],
        "large_ratio": metrics["tail_to_parent_ratio"] >= TARGET["min_tail_to_parent_ratio"],
    }
    valid = all(admissibility.values())
    passed = valid and all(witness_checks.values())
    factors = {
        "parent": min(1.0, TARGET["parent_threshold_eh"] / max(metrics["max_abs_triple_eh"], TARGET["ratio_floor_eh"])),
        "tail": min(1.0, metrics["tail_eh"] / TARGET["min_tail_eh"]),
        "ratio": min(1.0, metrics["tail_to_parent_ratio"] / TARGET["min_tail_to_parent_ratio"]),
    }
    return {
        "valid": valid,
        "passed": passed,
        "core_score": min(factors.values()) if valid else 0.0,
        "worst_family_score": None,
        "reason": "witness passes" if passed else ("admissible, target not met" if valid else "inadmissible Hamiltonian"),
        "admissibility": admissibility,
        "witness_checks": witness_checks,
        "score_factors": factors,
    }


def run(path):
    started = time.perf_counter()
    try:
        metrics = calculate(*read_candidate(path))
        report = assess(metrics)
        report["metrics"] = {key: value for key, value in metrics.items() if key not in ("subset_energies_eh", "increments_eh")}
    except (ValueError, TypeError, OSError, OverflowError, RecursionError, MemoryError, np.linalg.LinAlgError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=None, reason="invalid witness: " + str(error))
    report.update(worker_runtime_seconds=time.perf_counter() - started, peak_memory_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0)
    return report


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_AS, (TARGET["evaluator_memory_mib"] * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (TARGET["evaluator_cpu_seconds"],) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    print(json.dumps(run(sys.argv[1]), allow_nan=False))

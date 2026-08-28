"""Local numerical checks using analytic models and the supplied smoke input."""

import os
import sys
import time
import resource

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from scipy import linalg

from leads import Lead
from transport import solve_transport, prepare_leads, device_hamiltonian


def decimation(onsite, coupling, energy, eta):
    surface = onsite.copy()
    bulk = onsite.copy()
    forward = coupling.conj().T.copy()
    backward = coupling.copy()
    identity = np.eye(len(onsite))
    for iteration in range(100):
        propagated = linalg.solve((energy + 1j * eta) * identity - bulk,
                                  np.column_stack((forward, backward)))
        green_forward = propagated[:, :len(onsite)]
        green_backward = propagated[:, len(onsite):]
        correction = forward @ green_backward
        surface += correction
        bulk += correction + backward @ green_forward
        forward = forward @ green_forward
        backward = backward @ green_backward
        if max(linalg.norm(forward), linalg.norm(backward)) < 1e-13:
            break
    return coupling.conj().T @ linalg.solve(
        (energy + 1j * eta) * identity - surface, coupling)


def validate(example):
    random = np.random.default_rng(142)
    for size in (1, 2, 3, 5, 8):
        onsite = np.diag(-np.ones(size - 1), 1).astype(complex)
        onsite += onsite.conj().T
        coupling = np.zeros_like(onsite)
        coupling[0, -1] = -1
        lead = Lead(onsite, coupling)
        for energy in (-3.0, -1.1, 0.0, 0.6, 3.0):
            sigma, injection, count = lead.evaluate(energy)
            if abs(energy) < 2:
                expected = (energy - 1j * np.sqrt(4 - energy**2)) / 2
            else:
                expected = (energy - np.sign(energy) * np.sqrt(energy**2 - 4)) / 2
            target = np.zeros_like(onsite)
            target[-1, -1] = expected
            assert linalg.norm(sigma - target) < 1e-9, (size, energy, sigma)
            assert count == int(abs(energy) < 2)
    print("Analytic chains, nonminimal layers, and isolated-layer poles: passed", flush=True)
    for size in (3, 6, 12):
        for rank in (1, size // 2, size):
            matrix = random.normal(size=(size, size)) + 1j * random.normal(size=(size, size))
            onsite = (matrix + matrix.conj().T) / (2 * np.sqrt(size))
            left = random.normal(size=(size, rank)) + 1j * random.normal(size=(size, rank))
            right = random.normal(size=(size, rank)) + 1j * random.normal(size=(size, rank))
            coupling = left @ right.conj().T / size
            lead = Lead(onsite, coupling)
            for energy in (-0.31, 0.137, 1.271):
                sigma, injection, count = lead.evaluate(energy)
                residual = sigma - coupling.conj().T @ linalg.solve(
                    energy * np.eye(size) - onsite - sigma, coupling)
                assert linalg.norm(residual) < 1e-7 * max(1, linalg.norm(sigma))
                reference = decimation(onsite, coupling, energy, 1e-8)
                assert linalg.norm(sigma - reference) < 1e-5 * max(1, linalg.norm(sigma))
    print("Random complex and rank-deficient leads versus decimation: passed", flush=True)
    case = {
        "h_R": np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]]),
        "h_matrices": np.array([0, -1, -1, -1, -1], dtype=complex).reshape(5, 1, 1),
        "cells": np.array([[0, 0, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0]]),
        "potential": np.zeros((4, 1)),
        "energies": np.array([0.0, 1.3]),
        "lead_count": np.array(3),
    }
    for index, endpoint in enumerate(case["cells"][1:]):
        case[f"lead_cells_{index}"] = endpoint[None]
        case[f"lead_period_{index}"] = endpoint.copy()
        case[f"lead_shift_{index}"] = np.array(0.0)
    result = solve_transport(case)
    for index, energy in enumerate(case["energies"]):
        probability = (4 - energy**2) / (9 - 2 * energy**2)
        target = np.full((3, 3), probability)
        np.fill_diagonal(target, 1 - 2 * probability)
        assert np.max(abs(result["transmission"][index] - target)) < 1e-10
        assert np.max(abs(result["lb_conductance"][index].sum(axis=1))) < 1e-10
        assert abs(result["partition_noise"][index, 1, 0] - probability * (1 - probability)) < 1e-10
    print("Analytic three-terminal junction and partition noise: passed", flush=True)
    case = dict(np.load(example))
    baseline = solve_transport(case)
    reordered = {key: value.copy() for key, value in case.items()}
    cell_order = random.permutation(len(case["cells"]))
    reordered["cells"] = case["cells"][cell_order]
    reordered["potential"] = case["potential"][cell_order]
    for index in range(int(case["lead_count"])):
        lead_order = random.permutation(len(case[f"lead_cells_{index}"]))
        reordered[f"lead_cells_{index}"] = case[f"lead_cells_{index}"][lead_order]
    permuted = solve_transport(reordered)
    for key in ("transmission", "channels", "partition_noise", "lb_conductance"):
        assert np.max(abs(baseline[key] - permuted[key])) < 1e-9, key
    case["potential"] = np.zeros_like(case["potential"])
    uniform = solve_transport(case)
    assert np.max(abs(uniform["transmission"][0] - np.array([[0, 3], [3, 0]]))) < 1e-9
    print("Supplied Si model: cell-order invariance and perfect uniform transport passed", flush=True)


def benchmark(example, length, width, height, energy_count):
    start = time.perf_counter()
    case = dict(np.load(example))
    cells = np.array([(along, transverse, vertical)
                      for along in range(length)
                      for transverse in range(width)
                      for vertical in range(height)])
    case["cells"] = cells
    orbital_count = case["h_matrices"].shape[1]
    gate = 0.4 * np.exp(-((cells[:, 0] - length / 2) / (length / 10))**2)
    case["potential"] = np.repeat(gate[:, None], orbital_count, axis=1)
    case["lead_cells_0"] = cells[cells[:, 0] < 4]
    case["lead_cells_1"] = cells[cells[:, 0] >= length - 4]
    case["energies"] = np.linspace(6.6, 6.9, energy_count)
    original_evaluate = Lead.evaluate

    def timed_evaluate(lead, energy):
        before = time.perf_counter()
        answer = original_evaluate(lead, energy)
        print("lead", lead.size, lead.rank, "modes", answer[-1], "time", time.perf_counter() - before, flush=True)
        return answer

    Lead.evaluate = timed_evaluate
    result = solve_transport(case)
    print("device", len(cells) * orbital_count, "orbitals", "elapsed", time.perf_counter() - start,
          "max RSS MiB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, flush=True)
    print("modes", result["mode_counts"], "T", result["transmission"], flush=True)
    print("conservation", np.max(abs(result["lb_conductance"].sum(axis=1))),
          np.max(abs(result["lb_conductance"].sum(axis=2))), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        validate(sys.argv[1])
    else:
        benchmark(sys.argv[1], *map(int, sys.argv[2:]))

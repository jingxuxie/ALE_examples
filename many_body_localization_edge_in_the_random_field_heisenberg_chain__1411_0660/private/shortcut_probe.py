import argparse
import csv
import json
import resource
import time
from pathlib import Path

import numpy as np
import scipy
from scipy import sparse
from scipy.linalg import eigh, svdvals
from scipy.sparse.linalg import eigsh
from scipy.special import xlogy


def physical_instance(length, family, disorder, seed):
    generator = np.random.default_rng(seed)
    states = np.array(
        [state for state in range(1 << length) if state.bit_count() == length // 2],
        dtype=np.int64,
    )
    spins = ((states[:, None] >> np.arange(length)) & 1) - 0.5
    fields = generator.uniform(-disorder, disorder, length)
    if family == "quasiperiodic_ring":
        fields = disorder * np.cos(
            2 * np.pi * (np.sqrt(5) - 1) / 2 * np.arange(length)
            + generator.uniform(0, 2 * np.pi)
        )
    bonds = [(site, site + 1, 0.0) for site in range(length - 1)]
    if family != "open_chain":
        bonds.append((length - 1, 0, 0.73 if family == "flux_ring" else 0.0))
    if family == "two_leg_ladder":
        half_length = length // 2
        bonds = [
            (site, site + 1, 0.0)
            for site in range(length - 1)
            if site != half_length - 1
        ] + [(site, site + half_length, 0.0) for site in range(half_length)]
    diagonal = -spins @ fields
    row_parts = [np.arange(len(states))]
    column_parts = [np.arange(len(states))]
    value_parts = [diagonal]
    for first_site, second_site, phase in bonds:
        diagonal += spins[:, first_site] * spins[:, second_site]
        rows = np.flatnonzero(spins[:, first_site] != spins[:, second_site])
        flipped = states[rows] ^ (1 << first_site) ^ (1 << second_site)
        columns = np.searchsorted(states, flipped)
        amplitudes = np.full(len(rows), 0.5)
        if family == "flux_ring":
            amplitudes = amplitudes * np.exp(
                2j * phase * spins[rows, first_site]
            )
        row_parts.append(rows)
        column_parts.append(columns)
        value_parts.append(amplitudes)
    hamiltonian = sparse.coo_matrix(
        (
            np.concatenate(value_parts),
            (np.concatenate(row_parts), np.concatenate(column_parts)),
        ),
        shape=(len(states), len(states)),
    ).tocsc()
    return states, spins, hamiltonian


def observe(length, states, spins, energies, eigenvectors):
    probabilities = np.abs(eigenvectors) ** 2
    spacings = np.diff(energies)
    ratios = np.minimum(spacings[:-1], spacings[1:]) / np.maximum(
        spacings[:-1], spacings[1:]
    )
    entropies = []
    for eigenvector in eigenvectors.T:
        full_state = np.zeros(1 << length, dtype=eigenvector.dtype)
        full_state[states] = eigenvector
        schmidt_probabilities = svdvals(
            full_state.reshape(1 << (length // 2), -1)
        ) ** 2
        entropies.append(-np.sum(xlogy(schmidt_probabilities, schmidt_probabilities)))
    magnetization = spins[:, : length // 2].sum(axis=1)
    fluctuations = magnetization**2 @ probabilities - (
        magnetization @ probabilities
    ) ** 2
    log_probabilities = np.log(np.maximum(probabilities, np.finfo(float).tiny))
    divergence = np.sum(
        probabilities[:, :-1]
        * (log_probabilities[:, :-1] - log_probabilities[:, 1:]),
        axis=0,
    )
    spin_density = spins @ np.exp(2j * np.pi * np.arange(length) / length)
    dynamic_fraction = 1 - np.abs(spin_density @ probabilities) ** 2 / (
        np.abs(spin_density) ** 2 @ probabilities
    )
    return {
        "gap_ratio": float(np.mean(ratios)),
        "entanglement": float(np.mean(entropies)),
        "fluctuations": float(np.mean(fluctuations)),
        "participation_1": float(np.mean(-np.sum(xlogy(probabilities, probabilities), axis=0))),
        "participation_2": float(np.mean(-np.log(np.sum(probabilities**2, axis=0)))),
        "adjacent_kl": float(np.mean(divergence)),
        "dynamic_fraction": float(np.mean(dynamic_fraction)),
    }


def run_case(length, family, disorder, epsilon, seed):
    started = time.perf_counter()
    states, spins, hamiltonian = physical_instance(length, family, disorder, seed)
    dimension = len(states)
    initial = np.random.default_rng(seed + 1).normal(size=dimension)
    minimum = float(eigsh(hamiltonian, k=1, which="SA", v0=initial, return_eigenvectors=False)[0])
    maximum = float(eigsh(hamiltonian, k=1, which="LA", v0=initial, return_eigenvectors=False)[0])
    target = maximum - epsilon * (maximum - minimum)
    energies, eigenvectors = eigsh(
        hamiltonian, k=24, sigma=target, which="LM", tol=1e-11, v0=initial
    )
    order = np.argsort(energies)
    energies = energies[order]
    eigenvectors = eigenvectors[:, order]
    solving_seconds = time.perf_counter() - started
    residual = np.linalg.norm(
        hamiltonian @ eigenvectors - eigenvectors * energies, axis=0
    ) / max(1.0, abs(minimum), abs(maximum))
    orthogonality = np.linalg.norm(
        eigenvectors.conj().T @ eigenvectors - np.eye(len(energies)), ord=2
    )
    dense_error = None
    if length == 8:
        all_energies = eigh(hamiltonian.toarray(), eigvals_only=True)
        nearest = np.sort(all_energies[np.argsort(np.abs(all_energies - target))[:24]])
        dense_error = float(np.max(np.abs(nearest - energies)))
    observables = observe(length, states, spins, energies, eigenvectors)
    return {
        "family": family,
        "length": length,
        "dimension": dimension,
        "disorder": disorder,
        "epsilon": epsilon,
        "seed": seed,
        "solving_seconds": solving_seconds,
        "total_seconds": time.perf_counter() - started,
        "max_relative_residual": float(np.max(residual)),
        "orthogonality_error": float(orthogonality),
        "dense_eigenvalue_error": dense_error,
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        **observables,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    families = [
        "iid_periodic_chain",
        "open_chain",
        "flux_ring",
        "quasiperiodic_ring",
        "two_leg_ladder",
    ]
    rows = []
    started = time.perf_counter()
    for family in families:
        for length in (8, 12, 14):
            row = run_case(length, family, 3.0, 0.5, 4117)
            rows.append(row)
            print(json.dumps(row), flush=True)
    for disorder in (0.8, 6.0):
        for epsilon in (0.2, 0.5, 0.8):
            row = run_case(14, "iid_periodic_chain", disorder, epsilon, 9241)
            rows.append(row)
            print(json.dumps(row), flush=True)
    with (arguments.output / "probe.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "purpose": "Private pre-construction shortcut feasibility check, not a participant attempt or a reference solution.",
        "limitations": [
            "One realization per configuration; no statistical or thermodynamic conclusion is justified.",
            "No finite-size scaling or original paper phase diagram reproduction was attempted.",
            "The extension geometries are not claimed to be original-paper datasets.",
            "This does not empirically establish a frontier-agent task score.",
        ],
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "cases": len(rows),
        "elapsed_seconds": time.perf_counter() - started,
        "max_relative_residual": max(row["max_relative_residual"] for row in rows),
        "max_orthogonality_error": max(row["orthogonality_error"] for row in rows),
        "max_dense_eigenvalue_error": max(
            row["dense_eigenvalue_error"] for row in rows if row["dense_eigenvalue_error"] is not None
        ),
        "families": {
            family: {
                "cases": sum(row["family"] == family for row in rows),
                "total_seconds": sum(row["total_seconds"] for row in rows if row["family"] == family),
                "worst_residual": max(row["max_relative_residual"] for row in rows if row["family"] == family),
            }
            for family in families
        },
    }
    (arguments.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.linalg import null_space
from scipy.optimize import linprog, minimize_scalar, root


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from physics import EliashbergSolver, constraint_report, json_write, load_instance


def initialize():
    input_dir = ROOT / "participant" / "input"
    reference_path = input_dir / "reference.npz"
    if reference_path.exists():
        return
    rows = np.array([.2, .3, .45, .65, 1., 1.5, 2.1, 2.7])
    fractions = np.array([.425, .15, .425])
    features = np.linspace(-1, 1, 8)
    seed = np.exp(1.2 * np.outer(features, features))
    np.fill_diagonal(seed, 0)
    degrees = 8 * rows - .4
    solution = root(
        lambda logscale: np.exp(logscale) * (seed @ np.exp(logscale)) - degrees,
        np.log(np.sqrt(degrees / 7)), tol=1e-11,
    )
    if np.max(np.abs(solution.fun)) > 1e-8:
        raise RuntimeError("reference scaling failed")
    scale = np.exp(solution.x)
    aggregate = seed * np.outer(scale, scale) + .4 * np.eye(8)
    reference = fractions[:, None, None] * aggregate
    weights = np.full(8, 1 / 8)
    config = json.loads((input_dir / "config.json").read_text())
    if reference.min() < config["entry_lower"] or reference.max() > config["entry_upper"]:
        raise RuntimeError("reference violates the frozen entry bounds")
    with reference_path.open("xb") as stream:
        np.savez_compressed(
            stream, reference=reference, weights=weights,
            energies_mev=np.array([4., 25., 100.]), row_sums=reference @ weights,
            diagonal=np.diagonal(reference, axis1=1, axis2=2), static=reference.sum(axis=0),
        )
    json_write(ROOT / "evaluator" / "hidden" / "provenance.json", {
        "generator": "curator_search.py initialize", "numpy": np.__version__, "scipy": scipy.__version__,
        "rows_requested": rows.tolist(), "fractions": fractions.tolist(),
        "assortativity_parameter": 1.2, "static_diagonal": .4,
        "reference_minimum": float(reference.min()), "reference_maximum": float(reference.max()),
        "target_frozen": config["target_ratio"], "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "model_electronic_scale_mev": 20000,
        "maximum_lambda_omega_over_electronic_scale": float(rows.max() * 100 / 20000),
    })


def directions():
    edges = list(zip(*np.triu_indices(8, 1)))
    incidence = np.zeros((8, len(edges)))
    for edge, (left, right) in enumerate(edges):
        incidence[left, edge] = incidence[right, edge] = 1
    edge_basis = null_space(incidence)
    basis = np.zeros((edge_basis.shape[1], 8, 8))
    for edge, (left, right) in enumerate(edges):
        basis[:, left, right] = basis[:, right, left] = edge_basis[edge]
    return np.stack((
        np.concatenate((basis, np.zeros_like(basis))),
        np.concatenate((np.zeros_like(basis), basis)),
        np.concatenate((-basis, -basis)),
    ), axis=1)


def search(cpu_seconds, seed):
    instance = load_instance(ROOT / "participant" / "input")
    reference = instance["reference"]
    config = dict(instance["config"])
    config["temperature_bracket_kelvin"] = [10., 180.]
    config["root_xtol_kelvin"] = .003
    config["eigenvalue_tolerance"] = 1e-9
    basis = directions()
    flat = basis.reshape(len(basis), -1).T
    inequalities = np.concatenate((flat, -flat))
    margin = 2e-7
    bounds = np.concatenate((
        (config["entry_upper"] - margin - reference).ravel(),
        (reference - config["entry_lower"] - margin).ravel(),
    ))
    generators = np.random.RandomState(seed)
    family_solvers = [EliashbergSolver(
        instance["weights"], instance["row_sums"],
        instance["energies_mev"] * np.asarray(family["energy_factors"]), config,
    ) for family in config["families"]]
    started = time.process_time()
    log_path = ROOT / "evaluator" / "hidden" / "search.jsonl"
    best_score = 1.
    best_pair = np.stack([reference, reference])
    best_coordinates = np.zeros((2, len(basis)))
    restart = 0

    def materialize(coordinates):
        return reference + np.einsum("a,asij->sij", coordinates, basis)

    def emit(record):
        record["cpu_seconds"] = time.process_time() - started
        with log_path.open("a") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        print(json.dumps(record), flush=True)

    emit({"event": "start", "seed": seed, "cpu_budget": cpu_seconds, "dimension": len(basis), "input_sha256": instance["input_sha256"]})
    while restart < 80 and time.process_time() - started < cpu_seconds:
        endpoints = []
        coordinates_pair = []
        solver = family_solvers[restart % len(family_solvers)]
        for direction in (1, -1):
            if restart == 0:
                coordinates = np.zeros(len(basis))
            elif restart % 3 == 1:
                coordinates = best_coordinates[0 if direction == 1 else 1].copy()
            else:
                random_vertex = linprog(
                    generators.normal(size=len(basis)), A_ub=inequalities, b_ub=bounds,
                    bounds=[(None, None)] * len(basis), method="highs",
                )
                if not random_vertex.success:
                    raise RuntimeError(random_vertex.message)
                coordinates = .8 * random_vertex.x
            for iteration in range(12):
                modes = materialize(coordinates)
                temperature = solver.critical_temperature(modes, 64)["tc_kelvin"]
                derivative = solver.eigenpair(modes, temperature, 64, gradient=True)["gradient"]
                gradient = np.einsum("sij,asij->a", derivative, basis)
                proposal = linprog(
                    -direction * gradient, A_ub=inequalities, b_ub=bounds,
                    bounds=[(None, None)] * len(basis), method="highs",
                )
                if not proposal.success:
                    raise RuntimeError(proposal.message)
                displacement = proposal.x - coordinates
                if np.linalg.norm(displacement) < 1e-8:
                    break
                if direction == 1:
                    amount = 1.
                else:
                    amount = minimize_scalar(
                        lambda fraction: solver.eigenpair(materialize(coordinates + fraction * displacement), temperature, 64)["eigenvalue"],
                        bounds=(0, 1), method="bounded", options={"xatol": .002},
                    ).x
                coordinates += amount * displacement
                if time.process_time() - started >= cpu_seconds:
                    break
            endpoints.append(materialize(coordinates))
            coordinates_pair.append(coordinates)
        pair = np.stack(endpoints)
        constraints, canonical = constraint_report(pair, instance)
        if not constraints["admissible"]:
            raise RuntimeError("search left feasible set: " + str(constraints))
        temperatures = [[family_solver.critical_temperature(modes, 96)["tc_kelvin"] for modes in pair] for family_solver in family_solvers]
        score = min(values[0] / values[1] for values in temperatures)
        emit({"event": "restart", "restart": restart, "score96": score, "temperatures": temperatures})
        if score > best_score:
            best_score = score
            best_pair = pair
            best_coordinates = np.stack(coordinates_pair)
            with (ROOT / "evaluator" / "hidden" / "witness.npz").open("wb") as stream:
                np.savez_compressed(stream, kernels=best_pair)
            with (ROOT / "evaluator" / "hidden" / "search_state.npz").open("wb") as stream:
                np.savez_compressed(stream, coordinates=best_coordinates, basis=basis)
            emit({"event": "champion", "score96": best_score, "restart": restart})
        restart += 1
    json_write(ROOT / "evaluator" / "hidden" / "search_summary.json", {
        "seed": seed, "restarts": restart, "cpu_seconds": time.process_time() - started,
        "score96": best_score, "target_ratio": instance["config"]["target_ratio"],
        "input_sha256": instance["input_sha256"], "independently_verified": False,
        "numpy": np.__version__, "scipy": scipy.__version__,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize-only", action="store_true")
    parser.add_argument("--cpu-seconds", type=float, default=600.)
    parser.add_argument("--seed", type=int, default=12113345)
    arguments = parser.parse_args()
    initialize()
    if not arguments.initialize_only:
        search(arguments.cpu_seconds, arguments.seed)


if __name__ == "__main__":
    main()

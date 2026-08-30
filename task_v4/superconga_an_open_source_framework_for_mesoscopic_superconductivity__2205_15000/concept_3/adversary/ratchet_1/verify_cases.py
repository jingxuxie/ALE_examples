import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np
from scipy.linalg import eigh, solve

import evaluate


def independent_matrix(scene):
    chain = np.diag(np.ones(7), 1) + np.diag(np.ones(7), -1)
    normal = 0.7 * np.eye(64) - np.kron(np.eye(8), chain) - np.kron(chain, np.eye(8))
    for impurity in scene["impurities"]:
        normal[impurity["site"], impurity["site"]] += impurity["strength"]
    row, column = np.indices((8, 8))
    delta = np.full((8, 8), 0.55, dtype=complex)
    for center in scene["vortices"]:
        center_row, center_column = divmod(center, 3)
        displacement = column - (1.5 + 2 * center_column) + 1j * (row - (1.5 + 2 * center_row))
        radius = abs(displacement)
        delta *= np.tanh(radius / 1.15) * displacement / radius
    pair = np.diag(delta.ravel())
    return np.block([[normal, pair], [pair.conj(), -normal]])


def independent_metrics(truth, estimate):
    true_potential = np.zeros(64)
    predicted_potential = np.zeros(64)
    for impurity in truth["impurities"]:
        true_potential[impurity["site"]] = impurity["strength"]
    for impurity in estimate["impurities"]:
        predicted_potential[impurity["site"]] = impurity["strength"]
    true_sites = true_potential != 0
    predicted_sites = predicted_potential != 0
    support_f1 = 2 * np.sum(true_sites & predicted_sites) / (np.sum(true_sites) + np.sum(predicted_sites))
    strength_error = np.sqrt(np.sum((true_potential - predicted_potential) ** 2) / np.sum(true_potential ** 2))
    vortex_exact = sorted(truth["vortices"]) == sorted(estimate["vortices"])
    return {"support_f1": float(support_f1), "relative_strength_error": float(strength_error), "vortex_exact": int(vortex_exact)}


def audit_case(case, result=None):
    scene = evaluate.model.validate_scene(case["scene"])
    sampled = evaluate.model.draw_scene(case["seed"], case["family"])
    if sampled != scene:
        raise ValueError("scene not identical to public-prior seeded draw")
    matrix = independent_matrix(scene)
    trusted = evaluate.model.hamiltonian(evaluate.model.potential_of(scene), scene["vortices"])
    discrepancy = float(np.max(abs(matrix - trusted)))
    hermiticity = float(np.max(abs(matrix - matrix.conj().T)))
    eigenvalues, eigenvectors = eigh(matrix, check_finite=False)
    particle_hole = float(np.max(abs(eigenvalues + eigenvalues[::-1])))
    energies = np.asarray(evaluate.model.SPEC["energies"])
    table = abs(eigenvectors[:64]) ** 2 @ (0.065 / np.pi / ((energies[None, :] - eigenvalues[:, None]) ** 2 + 0.065 ** 2))
    trusted_table = evaluate.model.ldos_table(scene)
    table_error = float(np.max(abs(table - trusted_table)))
    actions = evaluate.model.uniform_actions(8, 5307)
    direct_error = 0.0
    for action in actions:
        site = action["site"]
        energy_index = action["energy_index"]
        source = np.zeros(128)
        source[site] = 1.0
        green_column = solve((energies[energy_index] + 0.065j) * np.eye(128) - matrix, source, check_finite=False)
        direct_error = max(direct_error, abs(-green_column[site].imag / np.pi - table[site, energy_index]))
    if max(discrepancy, hermiticity, particle_hole, table_error, direct_error) > 1e-10:
        raise ValueError("physics disagreement")
    report = {"id": case["id"], "prior_draw_exact": True, "matrix_max_error": discrepancy,
              "hermiticity_max_error": hermiticity, "particle_hole_max_error": particle_hole,
              "full_ldos_max_error": table_error, "direct_resolvent_max_error": float(direct_error)}
    if result is not None:
        query_actions = [entry["action"] for entry in result["transcript"]]
        observation_error = max((abs(entry["observation"]["value"] - table[entry["action"]["site"], entry["action"]["energy_index"]])
                                 for entry in result["transcript"]), default=0)
        if observation_error > 2e-11:
            raise ValueError("instrument observation mismatch")
        report["instrument_max_error"] = float(observation_error)
        if "estimate" in result:
            measured = independent_metrics(scene, result["estimate"])
            if any(abs(measured[key] - result["metrics"][key]) > 1e-12 for key in measured):
                raise ValueError("independent scoring mismatch")
            report["metrics_independently_verified"] = True
            predicted = evaluate.model.ldos_table(result["estimate"])
            indices = [(action["site"], action["energy_index"]) for action in query_actions]
            observed_residual = [predicted[site, energy_index] - table[site, energy_index] for site, energy_index in indices]
            report["estimated_scene_observed_rms"] = float(np.sqrt(np.mean(np.asarray(observed_residual) ** 2)))
            report["estimated_scene_full_grid_rms"] = float(np.sqrt(np.mean((predicted - table) ** 2)))
            report["estimated_scene_max_grid_difference"] = float(np.max(abs(predicted - table)))
        if query_actions:
            _, jacobian = evaluate.model.predict_potential(evaluate.model.potential_of(scene), scene["vortices"], query_actions, jacobian=True)
            columns = [evaluate.model.SPEC["impurity_sites"].index(impurity["site"]) for impurity in scene["impurities"]]
            singular = np.linalg.svd(jacobian[:, columns], compute_uv=False)
            report["truth_support_jacobian_min_singular"] = float(singular[-1])
            report["truth_support_jacobian_condition"] = float(singular[0] / singular[-1])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=HERE / "cases_96.json")
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "validity_96.json")
    arguments = parser.parse_args()
    if HERE not in arguments.output.resolve().parents:
        parser.error("output must stay in ratchet_1")
    cases = json.loads(arguments.cases.read_text())["episodes"]
    reports = []
    for case in cases:
        result = None
        if arguments.results is not None:
            result = json.loads((arguments.results / (case["id"] + ".json")).read_text())
        reports.append(audit_case(case, result))
    hashes = json.loads((HERE / "protected_hashes.json").read_text())
    changed = [name for name, digest in hashes.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changed:
        raise ValueError("protected assets changed: " + repr(changed))
    report = {"cases": len(cases), "all_valid": True, "protected_changes": changed, "episodes": reports,
              "independence": "Kronecker hopping and complex unit-vector pairing construction; independent metric formula; direct resolvent columns",
              "interpretation": "Jacobian and scene-separation diagnostics are not proof of global identifiability or a label-oracle solution"}
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(cases), "all_valid": True, "protected_changes": changed}))


if __name__ == "__main__":
    main()

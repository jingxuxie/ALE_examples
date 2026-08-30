"""Private staged-packet numerical, immutability, and parser audit."""

import copy
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
BASE = PACKET.parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
sys.path.insert(0, str(PACKET / "evaluator"))
sys.path.insert(0, str(PACKET / "evaluator" / "hidden"))
from adaptive import energy_error_gradient, probe_points
from adaptive_response import trusted_response
from api import CONSTRAINTS, artifact, robust_screen
from evaluate import evaluate_artifact, read_artifact
from independent import IndependentSystem
from oracle import DeterminantCC, random_pair_matrix
from stencil import stencil_points


def main():
    started = time.monotonic()
    checks = {}
    oracle = DeterminantCC()
    trusted = IndependentSystem()
    energies = np.array(CONSTRAINTS["orbital_energies"])
    original = json.loads((BASE / "participant" / "workspace" / "constraints.json").read_text())
    checks["all_original_thresholds_unchanged"] = all(CONSTRAINTS[key] == value for key, value in original.items())
    checks["public_private_thresholds_equal"] = CONSTRAINTS == json.loads((PACKET / "evaluator" / "hidden" / "constraints.json").read_text())
    data = json.loads((BASE / "champions" / "generation_3" / "submission.json").read_text())
    matrix, amplitudes = np.array(data["pair_matrix"]), np.array(data["amplitudes"])
    points, response = probe_points(matrix, amplitudes, oracle)
    independent = trusted_response(trusted, energies, matrix, amplitudes, 1e-12)
    error = float(np.max(abs(np.array(response["coordinates"]) - independent["coordinates"])))
    checks["public_trusted_gradient_agreement"] = error < 2e-10
    checks["coordinate_subset_bitwise_unchanged"] = all(metadata == original_metadata and np.array_equal(point, original_point)
        for (metadata, point), (original_metadata, original_point) in zip(points[:241], stencil_points(matrix)))
    checks["243_points"] = len(points) == 243 and [metadata["point"] for metadata, _ in points] == list(range(243))
    checks["all_displacements_same_radius"] = all(abs(np.linalg.norm(point - matrix) - 0.001) < 5e-15 for _, point in points[1:])
    checks["adaptive_opposite_signs"] = np.max(abs(points[241][1] + points[242][1] - 2 * matrix)) < 1e-14
    axes = []
    differences = []
    for row in range(15):
        for column in range(row, 15):
            axis = np.zeros((15, 15))
            axis[row, column] = axis[column, row] = 1.0 if row == column else 1 / np.sqrt(2)
            axes.append(axis)
            signed = []
            for sign in (1, -1):
                hamiltonian = oracle.hamiltonian(energies, matrix + sign * 1e-5 * axis)[0]
                result = oracle.solve(hamiltonian, amplitudes, tolerance=2e-12, max_evaluations=250)
                signed.append(result.energy - np.linalg.eigvalsh(hamiltonian)[0])
            differences.append((signed[0] - signed[1]) / 2e-5)
    fd_error = float(max(abs(np.array(differences) - response["coordinates"])))
    checks["all_120_gradient_coordinates_finite_difference"] = fd_error < 1e-7
    zero = artifact(np.zeros((15, 15)), np.zeros(18))
    zero_response = energy_error_gradient(zero["pair_matrix"], zero["amplitudes"], oracle)
    zero_independent = trusted_response(trusted, energies, np.zeros((15, 15)), np.zeros(18), 1e-12)
    checks["zero_gradient_deterministic_fallback"] = (zero_response["zero_gradient_fallback"]
        and zero_independent["zero_gradient_fallback"] and np.array_equal(zero_response["direction"], axes[0]))
    zero_points, _ = probe_points(np.zeros((15, 15)), np.zeros(18), oracle)
    checks["fallback_keeps_duplicate_certification_labels"] = (np.array_equal(zero_points[1][1], zero_points[241][1])
        and np.array_equal(zero_points[2][1], zero_points[242][1]))
    n2 = DeterminantCC(6, 2)
    n2_matrix = random_pair_matrix(np.random.default_rng(7162), 0.06)
    n2_hamiltonian = n2.hamiltonian(energies, n2_matrix)[0]
    n2_root = n2.solve(n2_hamiltonian, tolerance=2e-12)
    n2_response = energy_error_gradient(n2_matrix, n2_root.amplitudes, n2)
    checks["n2_exact_ccsd_zero_error_gradient"] = n2_response["norm"] < 1e-10
    boundary = np.zeros((15, 15))
    boundary[0, 0] = CONSTRAINTS["pair_entry_max"]
    boundary_report = robust_screen(boundary, np.zeros(18), oracle, check_paths=False)
    checks["no_clipping_or_physics_claim_for_domain_failure"] = (boundary_report["reason"] == "stencil_domain_failure"
        and boundary_report["physics_evaluated"] is False and boundary_report["core_score"] == 0)
    security_cases = {}
    with tempfile.TemporaryDirectory(prefix="ccsd-g4-audit-", dir=PACKET / "authoring") as temporary:
        directory = Path(temporary)
        good = directory / "valid.json"
        good.write_text(json.dumps(zero))
        security_cases["valid_parse"] = read_artifact(good, directory) == zero
        raw_cases = {"missing_keys": "{}", "nan": json.dumps(zero).replace("0.0", "NaN", 1),
                     "infinity": json.dumps(zero).replace("0.0", "Infinity", 1),
                     "overflow": json.dumps(zero).replace("0.0", "1e9999", 1),
                     "duplicate": json.dumps(zero)[:-1] + ',"schema_version":1}',
                     "oversize": " " * 65537, "invalid_utf8": b"\xff", "truncated": "["}
        for key, value in raw_cases.items():
            path = directory / (key + ".json")
            path.write_bytes(value if isinstance(value, bytes) else value.encode())
            report = evaluate_artifact(path, directory)
            security_cases[key] = report["passed"] is False and report["core_score"] == 0 and report["reason"].startswith("invalid_artifact")
        mutations = []
        for invalid in (True, "0", None, [], {}):
            for field in ("orbital_energies", "amplitudes"):
                changed = copy.deepcopy(zero)
                changed[field][0] = invalid
                mutations.append(changed)
            changed = copy.deepcopy(zero)
            changed["pair_matrix"][0][0] = invalid
            mutations.append(changed)
        for invalid in (True, 1.0, "1", 0, 2):
            changed = copy.deepcopy(zero)
            changed["schema_version"] = invalid
            mutations.append(changed)
        for field in zero:
            changed = copy.deepcopy(zero)
            del changed[field]
            mutations.append(changed)
        changed = copy.deepcopy(zero)
        changed["gradient"] = response["coordinates"]
        mutations.append(changed)
        for index, changed in enumerate(mutations):
            path = directory / ("mutation_" + str(index) + ".json")
            path.write_text(json.dumps(changed))
            report = evaluate_artifact(path, directory)
            security_cases["mutation_" + str(index)] = report["passed"] is False and report["core_score"] == 0
        link = directory / "link.json"
        link.symlink_to(good)
        dangling = directory / "dangling.json"
        dangling.symlink_to(PACKET / "authoring" / "not_readable_private_witness.json")
        linked_directory = directory / "linked_directory"
        linked_directory.symlink_to(directory, target_is_directory=True)
        fifo = directory / "fifo.json"
        os.mkfifo(fifo)
        for name, path, allowed in (("symlink", link, directory), ("dangling", dangling, directory),
                                   ("parent_symlink", linked_directory / "valid.json", directory),
                                   ("fifo", fifo, directory), ("outside", good, directory / "inside"),
                                   ("missing", directory / "missing.json", directory),
                                   ("directory", directory, directory)):
            report = evaluate_artifact(path, allowed)
            security_cases[name] = report["passed"] is False and report["core_score"] == 0
    checks["all_security_cases"] = all(security_cases.values())
    original_hashes = json.loads((PACKET / "authoring" / "active_generation_3_hashes.json").read_text())
    checks["active_and_archived_generation_three_unchanged"] = all(hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest
        for name, digest in original_hashes.items())
    checks = {name: bool(value) for name, value in checks.items()}
    security_cases = {name: bool(value) for name, value in security_cases.items()}
    report = {"passed": all(checks.values()), "checks": checks, "security_cases": security_cases,
              "public_trusted_gradient_max_error": error, "gradient_finite_difference_max_error": fd_error,
              "n2_gradient_norm": n2_response["norm"], "runtime_seconds": time.monotonic() - started}
    (PACKET / "authoring" / "packet_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

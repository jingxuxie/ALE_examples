import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


PILOT = Path(__file__).resolve().parents[3]
ROOT = PILOT.parent.parent
sys.path.insert(0, str(PILOT / "attempt"))
from response import responses
from symmetry import project_operators


specification = importlib.util.spec_from_file_location("pilot02_evaluator", PILOT / "private/evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_center_projection(payload):
    accumulated = np.zeros_like(payload["centers"])
    for operation_index, unitary in enumerate(payload["unitary"]):
        transformed = payload["centers"] @ payload["cartesian_rotations"][operation_index].T
        transformed += (payload["translations"][operation_index] - payload["orbital_shifts"][operation_index]) @ payload["lattice"]
        accumulated += np.abs(unitary) ** 2 @ transformed
    return accumulated / len(payload["unitary"])


def coefficient_vector_projection(payload):
    accumulated = {}
    count = len(payload["centers"])
    operation_count = len(payload["unitary"])
    for operation_index, unitary in enumerate(payload["unitary"]):
        shifts = payload["orbital_shifts"][operation_index]
        values = payload["connection"].conj() if payload["antiunitary"][operation_index] else payload["connection"]
        values = np.einsum("ab,rmnb->rmna", payload["cartesian_rotations"][operation_index], values)
        unique_shifts, labels = np.unique(shifts, axis=0, return_inverse=True)
        for left_label, left_shift in enumerate(unique_shifts):
            left = np.flatnonzero(labels == left_label)
            for right_label, right_shift in enumerate(unique_shifts):
                right = np.flatnonzero(labels == right_label)
                block = values[:, left][:, :, right]
                rotated = np.einsum("im,rmna,jn->rija", unitary[:, left], block, unitary[:, right].conj())
                images = payload["rvec"] @ payload["fractional_rotations"][operation_index].T + right_shift - left_shift
                for vector, matrix in zip(images, rotated):
                    key = tuple(int(component) for component in vector)
                    if key not in accumulated:
                        accumulated[key] = np.zeros((count, count, 3), complex)
                    accumulated[key] += matrix / operation_count
    vectors = np.array(sorted(accumulated), dtype=np.int64)
    matrices = np.array([accumulated[tuple(vector)] for vector in vectors])
    return vectors, matrices


def align(values, old_vectors, new_vectors):
    lookup = {tuple(vector): index for index, vector in enumerate(old_vectors)}
    result = np.zeros((len(new_vectors),) + values.shape[1:], dtype=values.dtype)
    for index, vector in enumerate(new_vectors):
        if tuple(vector) in lookup:
            result[index] = values[lookup[tuple(vector)]]
    return result


def support_residual(observed, expected, vectors):
    residual = observed - expected
    norms = np.linalg.norm(residual.reshape(len(residual), -1), axis=1)
    origin = np.flatnonzero(np.all(vectors == 0, axis=1))[0]
    squared = float(np.sum(norms ** 2))
    diagonal = np.arange(observed.shape[1])
    diagonal_squared = float(np.linalg.norm(residual[origin, diagonal, diagonal]) ** 2)
    return {"total_norm": float(np.sqrt(squared)), "origin_norm": float(norms[origin]),
            "origin_fraction_of_squared_error": float(norms[origin] ** 2 / max(squared, 1e-30)),
            "origin_diagonal_fraction_of_squared_error": diagonal_squared / max(squared, 1e-30),
            "top_R": [{"rvec": vectors[index].tolist(), "norm": float(norms[index])}
                      for index in np.argsort(norms)[-5:][::-1]]}


def main():
    watched = [PILOT / f"attempt/{name}" for name in ["solve.py", "symmetry.py", "response.py"]]
    watched += [ROOT / f"authoring/tournament/initial/02_operator_response_{split}_score.json" for split in ["test", "challenge"]]
    watched += [PILOT / "private/reference/manifest.json", PILOT / "participant/TASK.md", PILOT / "participant/workspace/SCHEMA.md"]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in watched}
    manifest = json.loads((PILOT / "private/reference/manifest.json").read_text())
    output = {"evidence": "valid initial attempt only; no interrupted attempt inspected", "unchanged_sha256": hashes, "cases": []}
    for split in ["test", "challenge"]:
        for record in manifest["splits"][split]:
            case_path = PILOT / record["input"]
            with np.load(case_path / "model.npz", allow_pickle=False) as archive:
                payload = {name: archive[name] for name in archive.files}
            metadata = json.loads((case_path / "case.json").read_text())
            expected = evaluator.load_npz(PILOT / record["reference"])
            weak = evaluator.load_npz(PILOT / record["weak_reference"])
            repaired = project_operators(payload)
            raw_response = responses(payload, metadata["occupied"])
            actual = dict(repaired, energies=raw_response[0], berry_raw=raw_response[1], optical_raw=raw_response[2])
            original_post = responses(dict(payload, **repaired), metadata["occupied"])
            actual.update(berry_repaired=original_post[1], optical_repaired=original_post[2])
            vectors, connection = coefficient_vector_projection(payload)
            centers = independent_center_projection(payload)
            corrected = dict(actual, rvec=vectors, ham=align(repaired["ham"], repaired["rvec"], vectors),
                             connection=connection, centers=centers)
            corrected_post = responses(dict(payload, **corrected), metadata["occupied"])
            corrected.update(berry_repaired=corrected_post[1], optical_repaired=corrected_post[2])
            observed_connection = align(repaired["connection"], repaired["rvec"], expected["rvec"])
            observed_ham = align(repaired["ham"], repaired["rvec"], expected["rvec"])
            origin = np.flatnonzero(np.all(expected["rvec"] == 0, axis=1))[0]
            diagonal = np.arange(len(centers))
            expected_diagonal = expected["connection"][origin, diagonal, diagonal].real
            diagonal_identity_error = np.linalg.norm(repaired["centers"] - expected["centers"] - expected_diagonal)
            causal = {}
            for branch, fix_centers, fix_connection in [("centers_only", True, False), ("connection_only", False, True), ("both_official_fields", True, True)]:
                operator_payload = dict(payload, rvec=expected["rvec"], ham=observed_ham,
                                        centers=expected["centers"] if fix_centers else repaired["centers"],
                                        connection=expected["connection"] if fix_connection else observed_connection)
                post = responses(operator_payload, metadata["occupied"])
                causal[branch] = {"berry_repaired": evaluator.relative_error(post[1], expected["berry_repaired"]),
                                  "optical_repaired": evaluator.relative_error(post[2], expected["optical_repaired"])}
            row = {"split": split, "name": record["name"], "material": record["material"],
                   "reproduced_submission": evaluator.score_arrays(actual, expected, weak),
                   "separate_projection_diagnostic": evaluator.score_arrays(corrected, expected, weak),
                   "connection_residual_location": support_residual(observed_connection, expected["connection"], expected["rvec"]),
                   "ham_residual_location": support_residual(observed_ham, expected["ham"], expected["rvec"]),
                   "official_origin_connection_diagonal_max": float(np.max(np.abs(expected_diagonal))),
                   "submitted_origin_connection_diagonal_max": float(np.max(np.abs(observed_connection[origin, diagonal, diagonal]))),
                   "center_difference_equals_official_AA_diagonal_absolute_residual": float(diagonal_identity_error),
                   "downstream_field_substitutions": causal}
            output["cases"].append(row)
            print(split, record["name"], "initial", row["reproduced_submission"]["score"],
                  "separate_projection", row["separate_projection_diagnostic"]["score"],
                  "AA_diag_max", row["official_origin_connection_diagonal_max"],
                  "diag_identity", diagonal_identity_error, flush=True)
    assert all(digest(ROOT / relative) == value for relative, value in hashes.items())
    output["initial_participant_attempt_and_records_preserved"] = True
    (Path(__file__).parent / "analysis.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

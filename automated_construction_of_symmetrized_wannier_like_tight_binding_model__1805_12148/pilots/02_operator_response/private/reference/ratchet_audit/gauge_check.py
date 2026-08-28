import hashlib
import json
from pathlib import Path
import sys

import numpy as np


PILOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PILOT / "private/reference"))
from oracle import make_native, response, rotate_response
from wannierberri.fourier.rvectors import Rvectors

sys.path.insert(0, str(PILOT / "attempt"))
from symmetry import project_operators


def relative(observed, expected):
    return float(np.linalg.norm(observed - expected) / max(np.linalg.norm(expected), 1e-12))


def official_response(metadata, payload):
    system, _ = make_native(metadata["material"])
    frame = np.asarray(metadata["frame"])
    inverse = np.argsort(metadata["native_order"])
    system._XX_R = {"Ham": payload["ham"][:, inverse][:, :, inverse],
                    "AA": np.einsum("ab,rmnb->rmna", frame.T, payload["connection"][:, inverse][:, :, inverse])}
    system.set_wannier_centers(wannier_centers_cart=payload["centers"][inverse] @ frame)
    system.clear_cached_wcc()
    system.rvec = Rvectors(lattice=system.real_lattice, iRvec=payload["rvec"],
                          shifts_left_red=system.wannier_centers_red)
    system.clear_cached_R()
    return rotate_response(response(system, payload["query_points"], metadata["occupied"]), frame)


def center_matrix_projection(payload):
    count = len(payload["centers"])
    accumulated = np.zeros((count, count, 3), complex)
    for operation_index, unitary in enumerate(payload["unitary"]):
        transformed = payload["centers"] @ payload["cartesian_rotations"][operation_index].T
        transformed += (payload["translations"][operation_index] - payload["orbital_shifts"][operation_index]) @ payload["lattice"]
        accumulated += np.einsum("in,na,jn->ija", unitary, transformed, unitary.conj())
    return accumulated / len(payload["unitary"])


def main():
    manifest = json.loads((PILOT / "private/reference/manifest.json").read_text())
    previous = json.loads((Path(__file__).parent / "analysis.json").read_text())
    result = {"method": "Official response evaluation of submitted repaired operators and exact diagonal-recentering controls", "cases": []}
    for split in ["test", "challenge"]:
        record = next(record for record in manifest["splits"][split] if record["material"] == "Te")
        case_path = PILOT / record["input"]
        metadata = json.loads((case_path / "case.json").read_text())
        with np.load(case_path / "model.npz", allow_pickle=False) as archive:
            original = {name: archive[name] for name in archive.files}
        with np.load(PILOT / record["reference"], allow_pickle=False) as archive:
            expected = {name: archive[name] for name in archive.files}
        submitted = project_operators(original)
        reference_payload = dict(original, **{name: expected[name] for name in ["rvec", "ham", "connection", "centers"]})
        submitted_payload = dict(original, **submitted)
        reference_response = official_response(metadata, reference_payload)
        submitted_response = official_response(metadata, submitted_payload)
        center_delta = submitted["centers"] - expected["centers"]
        diagonal = np.arange(len(center_delta))
        reference_origin = np.flatnonzero(np.all(expected["rvec"] == 0, axis=1))[0]
        recentered = dict(reference_payload, centers=submitted["centers"].copy(), connection=expected["connection"].copy())
        recentered["connection"][reference_origin, diagonal, diagonal] -= center_delta
        recentered_response = official_response(metadata, recentered)
        submitted_origin = np.flatnonzero(np.all(submitted["rvec"] == 0, axis=1))[0]
        normalized = dict(submitted_payload, centers=expected["centers"].copy(), connection=submitted["connection"].copy())
        normalized["connection"][submitted_origin, diagonal, diagonal] += center_delta
        normalized_response = official_response(metadata, normalized)
        physical_origin_residual = normalized["connection"][submitted_origin] - expected["connection"][reference_origin]
        projected_centers = center_matrix_projection(original)
        projected_centers[diagonal, diagonal] -= expected["centers"]
        row = {"name": record["name"], "split": split,
               "reference_reexecution_berry_relative_error": relative(reference_response[1], expected["berry_repaired"]),
               "reference_reexecution_optical_relative_error": relative(reference_response[2], expected["optical_repaired"]),
               "submitted_official_berry_relative_error": relative(submitted_response[1], expected["berry_repaired"]),
               "submitted_official_optical_relative_error": relative(submitted_response[2], expected["optical_repaired"]),
               "reference_recenter_gauge_berry_relative_error": relative(recentered_response[1], reference_response[1]),
               "reference_recenter_gauge_optical_relative_error": relative(recentered_response[2], reference_response[2]),
               "submitted_recenter_gauge_berry_relative_error": relative(normalized_response[1], submitted_response[1]),
               "submitted_recenter_gauge_optical_relative_error": relative(normalized_response[2], submitted_response[2]),
               "nongauge_origin_residual_norm_angstrom": float(np.linalg.norm(physical_origin_residual)),
               "nongauge_origin_residual_diagonal_max": float(np.max(np.abs(physical_origin_residual[diagonal, diagonal]))),
               "projected_center_matrix_explains_nongauge_residual_relative_error": relative(physical_origin_residual, projected_centers)}
        assert row["reference_reexecution_berry_relative_error"] < 1e-8
        assert row["reference_reexecution_optical_relative_error"] < 1e-8
        assert row["reference_recenter_gauge_berry_relative_error"] < 1e-8
        assert row["reference_recenter_gauge_optical_relative_error"] < 1e-8
        assert row["submitted_recenter_gauge_berry_relative_error"] < 1e-8
        assert row["submitted_recenter_gauge_optical_relative_error"] < 1e-8
        result["cases"].append(row)
        print(json.dumps(row, indent=2), flush=True)
    for relative_path, expected_digest in previous["unchanged_sha256"].items():
        path = PILOT.parent.parent / relative_path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest
    result["initial_artifacts_unchanged"] = True
    (Path(__file__).parent / "gauge_check.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

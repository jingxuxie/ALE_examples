"""Extract author-stored designs without executing the archived optimizer."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import shutil
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from physics import feasibility, geometry_digest, geometry_json, original_zigzag


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {
            ("numpy.core.multiarray", "_reconstruct"): np.core.multiarray._reconstruct,
            ("numpy.core.multiarray", "scalar"): np.core.multiarray.scalar,
            ("numpy", "ndarray"): np.ndarray,
            ("numpy", "dtype"): np.dtype,
        }
        if (module, name) not in allowed:
            raise pickle.UnpicklingError(f"Disallowed pickle global: {module}.{name}")
        return allowed[module, name]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    arguments = parser.parse_args()
    payload = arguments.archive.read_bytes()
    expected_md5 = "750859a1c2c847acdff9eda0ed24873e"
    if hashlib.md5(payload).hexdigest() != expected_md5:
        raise ValueError("Archive is not the verified Zenodo 7266609 v2 artifact")
    reference_root = ROOT / "private" / "reference"
    reference_root.mkdir(parents=True, exist_ok=True)
    archive_path = reference_root / "author_code.zip"
    if not archive_path.exists():
        shutil.copyfile(arguments.archive, archive_path)
    shutil.copyfile(ROOT / "participant" / "workspace" / "physics.py", reference_root / "physics.py")
    (ROOT / "attempt").mkdir(parents=True, exist_ok=True)
    specifications = [
        ("matched_1300", "homogeneous_filtered.p", "matched"),
        ("matched_980", "homogeneous_filtered_980.p", "matched"),
        ("doped_1300", "mismatched_filtered.p", "fixed"),
    ]
    manifest = {
        "archive_url": "https://zenodo.org/records/7266609/files/code.zip?download=1",
        "record_url": "https://zenodo.org/records/7266609",
        "paper_doi": "10.21468/SciPostPhys.14.3.047",
        "paper_arxiv": "2205.05689v3",
        "archive_md5": expected_md5,
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "archive_version": "v2",
        "archive_created": "2022-10-31",
        "record_publication_date": "2022-05-11",
        "paper_publication_date": "2023-03-23",
        "source_license": "BSD-3-Clause",
        "execution": "Archived optimizer was not executed. References are unmodified stored masks at epoch 800.",
        "grid_note": "Grid dimensions come from each stored mask; do not substitute the notebook's current L_y=1300 for the 61-row histories.",
        "cases": [],
    }
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        manifest["archive_members"] = [{"name": entry.filename, "bytes": entry.file_size} for entry in archive.infolist()]
        for request_id, filename, rule in specifications:
            member = "code/data/" + filename
            member_bytes = archive.read(member)
            data = RestrictedUnpickler(io.BytesIO(member_bytes)).load()
            original = data["masks_by_epoch"][-1]
            masks = {"sc_top": np.asarray(original["sc_top"], dtype=bool), "sc_bottom": np.asarray(original["sc_bot"], dtype=bool)}
            ny, nx = masks["sc_top"].shape
            region = {"mu_normal_mev": [10.0, 15.0], "zeeman_mev": [0.5, 1.5], "mu_sc_rule": rule}
            scenarios = [{"mu_normal_mev": 10.4, "zeeman_mev": 0.72}, {"mu_normal_mev": 12.3, "zeeman_mev": 1.05}, {"mu_normal_mev": 14.6, "zeeman_mev": 1.35}]
            if rule == "fixed":
                region.update(mu_normal_mev=[9.5, 10.5], zeeman_mev=[1.35, 1.65], mu_sc_mev=15.0)
                scenarios = [{"mu_normal_mev": 9.65, "zeeman_mev": 1.38}, {"mu_normal_mev": 10.0, "zeeman_mev": 1.50}, {"mu_normal_mev": 10.35, "zeeman_mev": 1.62}]
            request = {
                "schema_version": 1,
                "request_id": request_id,
                "grid": {"nx": nx, "ny": ny, "spacing_nm": 20.0, "period_nm": nx * 20.0, "height_nm": (ny - 1) * 20.0},
                "fixed_physics": {"kinetic_mev_nm2": 1905.0, "rashba_mev_nm": 20.0, "delta_mev": 1.0, "phase_rad": math.pi},
                "operating_region": region,
                "manufacturing": {"minimum_separation_nm": 100.0, "minimum_contact_rows": 6, "maximum_median_flips": math.ceil(nx / 2), "mirror_x_required": True},
                "budget": {"wall_seconds": 1200, "cpu_seconds": 2400, "memory_gib": 6, "cpu_cores": 2},
            }
            baseline = original_zigzag(request)
            request["baseline_geometry"] = geometry_json(baseline)
            case_directory = ROOT / "private" / "challenge_pool" / request_id
            write_json(case_directory / "request.json", request)
            write_json(case_directory / "scenarios.json", scenarios)
            strong = {"schema_version": 1, "request_id": request_id, "geometry": geometry_json(masks)}
            write_json(reference_root / f"{request_id}.json", strong)
            np.savez_compressed(reference_root / f"{request_id}_stored_outputs.npz", actual_gaps=np.asarray(data["actual_gaps"]), predicted_gaps=np.asarray(data["predicted_gaps"]), grid_gaps=np.asarray(data["gaps"]), wavefunction=np.asarray(data["wf"]))
            entry = {
                "request_id": request_id,
                "source_member": member,
                "source_member_sha256": hashlib.sha256(member_bytes).hexdigest(),
                "epoch": len(data["masks_by_epoch"]) - 1,
                "snapshots": len(data["masks_by_epoch"]),
                "geometry_sha256": geometry_digest(masks),
                "shape": [ny, nx],
                "dofs": 4 * nx * ny,
                "geometry_modifications": "none; sc_bot key renamed sc_bottom; unused empty gate masks omitted",
                "strong_feasibility": feasibility(request, masks),
                "weak_feasibility": feasibility(request, baseline),
                "stored_gap_values_mev": np.asarray(data["gaps"]).ravel().tolist(),
            }
            manifest["cases"].append(entry)
            print(request_id, entry["dofs"], entry["strong_feasibility"], flush=True)
            if not entry["strong_feasibility"]["valid"] or not entry["weak_feasibility"]["valid"]:
                raise ValueError(f"Stored reference or original zigzag violates constraints: {request_id}")
            if request_id == "matched_1300":
                example = dict(request, request_id="example")
                write_json(ROOT / "participant" / "input" / "example.json", example)
    manifest["private_physics_sha256"] = hashlib.sha256((reference_root / "physics.py").read_bytes()).hexdigest()
    write_json(reference_root / "manifest.json", manifest)


if __name__ == "__main__":
    main()

import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import time
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from oracle import PILOT, TASK_ROOT, export_model, export_symmetry, make_native, response, rotate_response


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def points_for(seed, count):
    generator = np.random.default_rng(seed)
    points = generator.uniform(0.08, 0.44, (count // 2, 3))
    return np.concatenate([points, -points])


def write_case(case_path, material, angles, spin_order, seed, count, reference_path=None):
    started = time.monotonic()
    case_path.mkdir(parents=True, exist_ok=True)
    system, symmetrizer = make_native(material)
    frame = Rotation.from_euler("zyx", angles, degrees=True).as_matrix()
    order = np.arange(system.num_wann)
    if spin_order == "block":
        order = np.concatenate([order[::2], order[1::2]])
    occupied = 18 if material == "Te" else 8
    points = points_for(seed, count)
    metadata = {"material": material, "occupied": occupied, "spin_order": spin_order,
                "native_order": order.tolist(), "frame": frame.tolist(),
                "operator_format": "center-subtracted phase-I", "orbital_order_is_fixed": True}
    (case_path / "case.json").write_text(json.dumps(metadata, indent=2) + "\n")
    payload = export_model(system, frame, order)
    payload.update(export_symmetry(symmetrizer, frame, order))
    payload["query_points"] = points
    np.savez_compressed(case_path / "model.npz", **payload)
    if reference_path is None:
        return None
    original = rotate_response(response(system, points, occupied), frame)
    repaired = copy.deepcopy(system)
    repaired.symmetrize2(symmetrizer, silent=True)
    post_response = rotate_response(response(repaired, points, occupied), frame)
    expected = export_model(repaired, frame, order)
    expected.update(energies=original[0], berry_raw=original[1], optical_raw=original[2],
                    berry_repaired=post_response[1], optical_repaired=post_response[2])
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(reference_path, **expected)
    baseline_path = reference_path.with_name(reference_path.stem + "_weak.npz")
    specification = importlib.util.spec_from_file_location("starter", PILOT / "participant/workspace/solve.py")
    starter = importlib.util.module_from_spec(specification)
    import sys
    sys.path.insert(0, str(PILOT / "participant/workspace"))
    specification.loader.exec_module(starter)
    np.savez_compressed(baseline_path, **starter.solve(case_path))
    internal_only = rotate_response(response(system, points, occupied, external_terms=False), frame)
    omission_error = float(np.linalg.norm(internal_only[1] - original[1]) / max(np.linalg.norm(original[1]), 1e-12))
    return {"material": material, "raw_R": len(payload["rvec"]), "repaired_R": len(expected["rvec"]),
            "num_wann": system.num_wann, "input_sha256": digest(case_path / "model.npz"),
            "reference_sha256": digest(reference_path), "reference_seconds": time.monotonic() - started,
            "external_term_omission_relative_error": omission_error}


def main():
    references = PILOT / "private/reference"
    references.mkdir(parents=True, exist_ok=True)
    source_root = TASK_ROOT / "authoring/sources"
    source_manifest = {}
    for material in ["Te", "Fe"]:
        source = source_root / f"WannierBerri-tutorial/tutorials/5_symmetrization/{material}_data/{material}_tb.dat"
        source_manifest[material] = {"path": str(source), "sha256": digest(source), "bytes": source.stat().st_size}
    source_manifest["wb_commit"] = "e046ddc4bfe026ba1f9af2376f04babac5677425"
    source_manifest["tutorial_commit"] = "efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb"
    source_manifest["packages"] = {name: importlib.metadata.version(name) for name in ["wannierberri", "irrep", "numpy", "scipy", "spglib"]}
    import wannierberri
    installed = Path(wannierberri.__file__).parent
    for module in ["symmetry/sym_wann_2.py", "formula/covariant.py", "calculators/dynamic.py"]:
        assert digest(installed / module) == digest(source_root / "wannier-berri/wannierberri" / module)
    (references / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    write_case(PILOT / "participant/input/smoke", "Te", [0, 0, 0], "block", 17021, 2)
    definitions = {
        "test": [("te_screw", "Te", [0, 0, 0], "interlace", 20101, 6)],
        "challenge": [("te_frame", "Te", [31, -17, 23], "block", 20201, 8),
                      ("fe_hybrid_frame", "Fe", [-27, 39, 11], "block", 20202, 8)],
        "confirmation": [("te_reserved_frame", "Te", [53, 19, -41], "block", 20301, 10),
                         ("fe_reserved_frame", "Fe", [-61, -29, 37], "interlace", 20302, 10)],
    }
    manifest = {"splits": {}, "confirmation_reserved_before_tournament": True}
    for split, cases in definitions.items():
        manifest["splits"][split] = []
        for name, material, angles, spin_order, seed, count in cases:
            reference_path = references / split / (name + ".npz")
            case_path = PILOT / "private/challenge_pool" / split / name
            record = write_case(case_path, material, angles, spin_order, seed, count, reference_path)
            record.update(name=name, input=str(case_path.relative_to(PILOT)), reference=str(reference_path.relative_to(PILOT)),
                          weak_reference=str(reference_path.with_name(name + "_weak.npz").relative_to(PILOT)))
            manifest["splits"][split].append(record)
            (references / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print("BUILT", split, name, record, flush=True)
    attempt = PILOT / "attempt"
    attempt.mkdir(exist_ok=True)
    for source in (PILOT / "participant/workspace").glob("*.py"):
        target = attempt / source.name
        if not target.exists():
            shutil.copy2(source, target)


if __name__ == "__main__":
    main()

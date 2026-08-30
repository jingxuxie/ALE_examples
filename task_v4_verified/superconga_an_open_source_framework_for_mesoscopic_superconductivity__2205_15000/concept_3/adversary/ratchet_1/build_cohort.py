import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

import evaluate


def features(scene):
    sites = np.asarray([item["site"] for item in scene["impurities"]])
    strengths = np.asarray([item["strength"] for item in scene["impurities"]])
    positions = np.column_stack((sites % 8, sites // 8))
    centers = np.asarray([evaluate.model.SPEC["vortex_centers"][value] for value in scene["vortices"]]).reshape(-1, 2)
    dipoles = []
    for first in range(len(sites)):
        for second in range(first + 1, len(sites)):
            if np.sum(abs(positions[first] - positions[second])) == 1 and strengths[first] * strengths[second] < 0:
                dipoles.append(abs(abs(strengths[first]) - abs(strengths[second])))
    near_core = int(np.sum(np.min(np.linalg.norm(positions[:, None] - centers[None, :], axis=2), axis=1) <= 0.8)) if len(centers) else 0
    return {"count": len(sites), "vortex_count": len(centers), "mixed_sign": bool(np.any(strengths > 0) and np.any(strengths < 0)),
            "opposite_adjacent_pairs": len(dipoles), "closest_dipole_mismatch": min(dipoles) if dipoles else None,
            "mean_abs_strength": float(np.mean(abs(strengths))), "min_abs_strength": float(np.min(abs(strengths))),
            "max_abs_strength": float(np.max(abs(strengths))), "strong_count": int(np.sum(abs(strengths) >= 1.25)),
            "core_separation": float(np.linalg.norm(centers[0] - centers[1])) if len(centers) == 2 else None,
            "near_core_impurities": near_core, "span_x": int(np.ptp(positions[:, 0]) + 1),
            "span_y": int(np.ptp(positions[:, 1]) + 1), "edge_count": int(np.sum(np.any((positions == 1) | (positions == 6), axis=1)))}


def accepts(scene, family, mode):
    item = features(scene)
    maximum = 5 if family == "dispersed" else 7
    if item["count"] != maximum or not item["mixed_sign"]:
        return False
    if mode == "weak_dipoles":
        return (item["closest_dipole_mismatch"] is not None and item["closest_dipole_mismatch"] <= 0.15
                and item["mean_abs_strength"] <= 1.05 and item["vortex_count"] >= 1)
    if mode == "overlapping_cores":
        return item["core_separation"] == 2.0 and item["near_core_impurities"] >= 2
    if mode == "strong_cluster":
        return (item["span_x"] <= 4 and item["span_y"] <= 4 and item["strong_count"] >= (maximum + 1) // 2
                and item["vortex_count"] >= 1)
    if mode == "edge_mixed":
        return item["edge_count"] >= (2 * maximum + 2) // 3 and item["min_abs_strength"] <= 0.7 and item["max_abs_strength"] >= 1.45
    raise ValueError(mode)


def snapshot_patch():
    print("*** Begin Patch")
    for filename in ("solve.py", "inference.py", "physics.py"):
        source = ROOT / "champions" / "generation_1" / filename
        destination = HERE / "submission" / filename
        if destination.exists():
            raise RuntimeError("staged champion already exists")
        print("*** Add File: " + str(destination))
        print("\n".join("+" + line for line in source.read_text().splitlines()))
    print("*** End Patch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-patch", action="store_true")
    arguments = parser.parse_args()
    if arguments.snapshot_patch:
        snapshot_patch()
        return
    destination = HERE / "cases_96.json"
    if destination.exists():
        raise RuntimeError("cohort already frozen")
    master_seed = secrets.randbits(128)
    generator = np.random.default_rng(master_seed)
    cases = []
    families = evaluate.model.SPEC["families"]
    for index in range(16):
        for family in families:
            seed = int(generator.integers(0, 2 ** 63))
            scene = evaluate.model.draw_scene(seed, family)
            cases.append({"id": "independent-" + family + "-" + str(index), "family": family, "cohort": "independent",
                          "mode": "unconditioned", "seed": seed, "scene": scene, "rejection_draws": 1, "features": features(scene)})
    for mode in ("weak_dipoles", "overlapping_cores", "strong_cluster", "edge_mixed"):
        for index in range(4):
            for family in families:
                for trial in range(200000):
                    seed = int(generator.integers(0, 2 ** 63))
                    scene = evaluate.model.draw_scene(seed, family)
                    if accepts(scene, family, mode):
                        break
                else:
                    raise RuntimeError("rejection sampler exhausted: " + family + "/" + mode)
                cases.append({"id": mode + "-" + family + "-" + str(index), "family": family, "cohort": "boundary",
                              "mode": mode, "seed": seed, "scene": scene, "rejection_draws": trial + 1, "features": features(scene)})
    manifest = {"schema": "ratchet-private-cohort-v1", "master_seed": master_seed, "episodes": cases,
                "selection": "48 independent draws; 48 rejection-conditioned draws from the identical public sampler, before any solver outcome is observed",
                "query_budget": 56, "cpu_seconds": 90, "wall_seconds": 120, "target_changed": False,
                "independent_count": 48, "boundary_count": 48}
    destination.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    protected = []
    for directory in (ROOT / "participant", ROOT / "evaluator", ROOT / "champions" / "generation_1"):
        protected.extend(path for path in directory.rglob("*") if path.is_file())
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(protected)}
    (HERE / "protected_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps({"cases": len(cases), "total_sampler_draws": sum(case["rejection_draws"] for case in cases)}))


if __name__ == "__main__":
    main()

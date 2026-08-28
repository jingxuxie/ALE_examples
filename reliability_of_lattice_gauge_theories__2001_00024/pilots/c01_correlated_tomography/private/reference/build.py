import copy
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
from scipy.optimize import linprog

from source_io import cell_value, read_workbook

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "source"
sys.path.insert(0, str(ROOT / "private"))
from scoring import losses


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def fitted_tracks(case):
    result = {}
    for track in case["tracks"]:
        calibration = track["calibration"]
        times = np.asarray(track["time_ms"])
        basis = 0.5 - 0.5 * np.exp(-times / calibration["decay_ms"]) * np.cos(
            2 * np.pi * times / calibration["period_ms"] + calibration["phase_rad"]
        )
        weighted_design = np.column_stack([np.ones(len(times)), basis]) / np.asarray(track["sigma"])[:, None]
        orthogonal, triangular = np.linalg.qr(weighted_design)
        coefficients = np.linalg.solve(triangular, orthogonal.T @ (np.asarray(track["signal"]) / track["sigma"]))
        inverse = np.linalg.inv(triangular)
        covariance = inverse @ inverse.T
        queries = np.asarray(track["query_time_ms"])
        query_basis = 0.5 - 0.5 * np.exp(-queries / calibration["decay_ms"]) * np.cos(
            2 * np.pi * queries / calibration["period_ms"] + calibration["phase_rad"]
        )
        result[track["id"]] = {
            "offset": float(coefficients[0]), "amplitude": float(coefficients[1]),
            "amplitude_se": float(np.sqrt(covariance[1, 1])),
            "prediction": (coefficients[0] + coefficients[1] * query_basis).tolist(),
        }
    return result


def certificate(result):
    if not result.success:
        raise RuntimeError(result.message)
    return {
        "primal": result.x.tolist(), "inequality_dual": result.ineqlin.marginals.tolist(),
        "equality_dual": float(result.eqlin.marginals[0]),
    }


def reference(case):
    fits = fitted_tracks(case)
    observations = case["occupation"]["observations"]
    matrix = np.asarray([row["response"] for row in observations], dtype=float)
    centers, radii = [], []
    for row in observations:
        if "center" in row:
            centers.append(row["center"])
            radii.append(row["radius"])
        else:
            centers.append(sum(fits[name]["amplitude"] * value for name, value in row["amplitude_weights"].items()))
            variance = sum(fits[name]["amplitude_se"] ** 2 * value ** 2 for name, value in row["amplitude_weights"].items())
            radii.append(row["systematic_radius"] + row["sigma_multiplier"] * np.sqrt(variance))
    centers, radii = np.asarray(centers), np.asarray(radii)
    size = matrix.shape[1]
    inequalities = np.r_[matrix, -matrix]
    limits = np.r_[centers + radii, radii - centers]
    relaxation = linprog(
        [0.0] * size + [1.0],
        A_ub=np.column_stack([inequalities, -np.r_[radii, radii]]), b_ub=limits,
        A_eq=[[1.0] * size + [0.0]], b_eq=[1.0], bounds=(0, None), method="highs-ds",
    )
    certificates = {"inflation": certificate(relaxation), "targets": {}}
    inflation = max(0.0, float(relaxation.x[-1]))
    enlarged = radii * (1 + inflation + case["occupation"]["feasibility_pad"])
    limits = np.r_[centers + enlarged, enlarged - centers]
    bounds = {}
    for target in case["occupation"]["targets"]:
        coefficients = np.asarray(target["coefficients"], dtype=float)
        extrema, proofs = [], {}
        for direction, name in [(1, "lower"), (-1, "upper")]:
            optimum = linprog(direction * coefficients, A_ub=inequalities, b_ub=limits,
                              A_eq=np.ones((1, size)), b_eq=[1.0], bounds=(0, None), method="highs-ds")
            proofs[name] = certificate(optimum)
            extrema.append(float(coefficients @ optimum.x))
        bounds[target["id"]] = extrema
        certificates["targets"][target["id"]] = proofs
    return {
        "fits": fits, "inflation": inflation, "bounds": bounds,
        "matrix": matrix.tolist(), "centers": centers.tolist(), "radii": radii.tolist(),
        "certificates": certificates,
    }


def extract_tracks(workbook, moment):
    column_index = [0, 30, 60, 90, 120].index(moment)
    columns = [chr(ord("A") + 3 * column_index + offset) for offset in range(3)]
    tracks, heldout, lineage = [], {}, []
    for sheet, identifier in zip(["Fig.a", "Fig.b", "Fig.c", "Fig.d"], ["A", "B", "C", "D"]):
        values = []
        for number in sorted(workbook[sheet]):
            sample = [cell_value(workbook[sheet], number, column) for column in columns]
            if all(isinstance(value, (int, float)) for value in sample):
                if sample[2] <= 0:
                    raise ValueError("Nonpositive source error bar")
                values.append((number, sample))
        selected = [entry for index, entry in enumerate(values) if index % 5 != 4]
        reserved = [entry for index, entry in enumerate(values) if index % 5 == 4]
        tracks.append({
            "id": identifier, "time_ms": [entry[1][0] for entry in selected],
            "signal": [entry[1][1] for entry in selected], "sigma": [entry[1][2] for entry in selected],
            "query_time_ms": [entry[1][0] for entry in reserved],
            "calibration": {"period_ms": 7.2, "decay_ms": 96.0, "phase_rad": 0.0},
        })
        heldout[identifier] = {"signal": [entry[1][1] for entry in reserved], "sigma": [entry[1][2] for entry in reserved]}
        lineage.append({"file": "ed_fig9.xlsx", "sheet": sheet, "columns": columns,
                        "visible_rows": [entry[0] for entry in selected], "heldout_rows": [entry[0] for entry in reserved]})
    return tracks, heldout, lineage


def make_case(workbook, densities, moment, family, split):
    tracks, heldout, lineage = extract_tracks(workbook, moment)
    states = list(itertools.product([0, 2], [0, 1], [0, 2])) if family == "projected" else list(itertools.product(range(4), repeat=3))
    split_response = [[0, 0.5, 1, 0.5], [0.5, 0.5, 0.5, 0.5], [1, 0.5, 0, 0], [0.5, 0.5, 0, 0]]
    density_row, density = densities[moment]
    observations = [
        {"id": "matter_mean", "response": [middle for left, middle, right in states],
         "center": density[0], "radius": 2.5 * density[1] + 0.015},
        {"id": "link_doublon", "response": [(int(left == 2) + int(right == 2)) / 2 for left, middle, right in states],
         "center": density[2], "radius": 2.5 * density[3] + 0.015},
    ]
    channels = [
        ("right_empty", {"A": 1.0}, [int(middle == 1 and right == 0) for left, middle, right in states]),
        ("left_empty", {"B": 1.0}, [int(middle == 1 and left == 0) for left, middle, right in states]),
        ("split_sum", {"C": 1.0, "D": 1.0}, [split_response[left][right] for left, middle, right in states]),
    ]
    for identifier, weights, response in channels:
        if family == "density_only" or (family == "one_matter_orientation" and identifier == "left_empty"):
            continue
        observations.append({
            "id": identifier, "response": response, "amplitude_weights": weights,
            "sigma_multiplier": 2.5, "systematic_radius": 0.025 * sum(abs(value) for value in weights.values()),
        })
    targets = []
    for identifier, allowed in [
        ("p010", [(0, 1, 0)]), ("p002", [(0, 0, 2)]), ("p200", [(2, 0, 0)]),
        ("p002_plus_p200", [(0, 0, 2), (2, 0, 0)]),
        ("gauge_valid", [(0, 1, 0), (0, 0, 2), (2, 0, 0)]),
    ]:
        targets.append({"id": identifier, "coefficients": [int(state in allowed) for state in states]})
    case = {
        "schema_version": 1, "case_id": f"{split}_{family}_t{moment:03d}", "family": family,
        "tracks": tracks, "occupation": {"states": states, "observations": observations,
                                            "targets": targets, "feasibility_pad": 1e-8},
    }
    lineage.append({"file": "fig2.xlsx", "sheet": "Fig.2c Experimental Data", "row": density_row,
                    "columns": ["A", "B", "C", "D", "E"]})
    return {"case": case, "source": {"ramp_time_ms": moment, "lineage": lineage, "heldout_readout": heldout}}


def main():
    workbook = read_workbook(SOURCE / "ed_fig9.xlsx")
    density_sheet = read_workbook(SOURCE / "fig2.xlsx")["Fig.2c Experimental Data"]
    densities = {}
    for number in sorted(density_sheet):
        values = [cell_value(density_sheet, number, column) for column in "ABCDE"]
        if all(isinstance(value, (int, float)) for value in values):
            densities[int(values[0])] = (number, values[1:])
    spec = importlib.util.spec_from_file_location("fixed_weak_baseline", ROOT / "private" / "reference" / "weak" / "solver.py")
    weak = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(weak)
    families = ["projected", "leakage", "one_matter_orientation", "density_only"]
    manifest = {"version": 1, "split_groups": {"screening": [0, 60, 90], "challenge": [30], "confirmation": [120]}, "files": []}
    for split, moments in manifest["split_groups"].items():
        entries = [make_case(workbook, densities, moment, family, split) for moment in moments for family in families]
        for entry in entries:
            entry["reference"] = reference(entry["case"])
            entry["reference"]["weak_losses"] = losses(entry["case"], entry["reference"], weak.solve(entry["case"]))
        dump(ROOT / "private" / "challenge_pool" / f"{split}.json", {"split": split, "cases": entries})
        if split == "screening":
            dump(ROOT / "participant" / "input" / "example_case.json", entries[0]["case"])
        if split == "challenge":
            candidates = copy.deepcopy(entries)
            for entry in candidates:
                entry["case"]["case_id"] = entry["case"]["case_id"].replace("challenge_", "candidate_sparse_")
                for track in entry["case"]["tracks"]:
                    for key in ["time_ms", "signal", "sigma"]:
                        track[key] = track[key][::2]
                for lineage in entry["source"]["lineage"][:4]:
                    lineage["visible_rows"] = lineage["visible_rows"][::2]
                entry["source"]["transformation"] = "Keep every second visible source row; do not fabricate noise."
                entry["reference"] = reference(entry["case"])
                entry["reference"]["weak_losses"] = losses(entry["case"], entry["reference"], weak.solve(entry["case"]))
            dump(ROOT / "private" / "challenge_pool" / "ratchet_candidates.json", {"split": "unused_candidates", "cases": candidates})
    for path in sorted(SOURCE.iterdir()):
        if path.is_file():
            content = path.read_bytes()
            manifest["files"].append({"name": path.name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "md5": hashlib.md5(content).hexdigest()})
    for split in manifest["split_groups"]:
        path = ROOT / "private" / "challenge_pool" / f"{split}.json"
        manifest[f"{split}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    dump(ROOT / "private" / "reference" / "manifest.json", manifest)
    print(json.dumps({"case_counts": {"screening": 12, "challenge": 4, "confirmation": 4, "unused_candidates": 4}, "manifest": str(ROOT / "private" / "reference" / "manifest.json")}))


if __name__ == "__main__":
    main()

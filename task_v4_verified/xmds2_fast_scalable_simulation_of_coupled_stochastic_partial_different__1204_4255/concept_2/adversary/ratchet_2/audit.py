import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from search_api import assess_member, certificate_screen
from simulator import quick


def perturb(base, point):
    result = dict(base)
    result["nonlinearity"] *= 1 + 0.02 * point[0]
    result["duration"] *= 1 + 0.02 * point[1]
    result["a1"] += 0.01 * point[2]
    result["a2"] += 0.01 * point[3]
    result["relative_phase"] += 0.03 * point[4]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", choices=("v_4", "v_3"))
    arguments = parser.parse_args()
    metadata = json.loads((ROOT / "attempts" / (arguments.artifact + ".run.json")).read_text())
    if metadata["status"] == "running":
        raise ValueError("active attempts must not be inspected")
    evaluation = json.loads((ROOT / "attempts" / (arguments.artifact + ".evaluation.json")).read_text())
    if not evaluation.get("valid") or not evaluation.get("passed") or not evaluation.get("complete_assessment"):
        raise ValueError("official complete pass required before audit")
    source = ROOT / "attempts" / arguments.artifact / "submission.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == evaluation["submission_sha256"]
    base = json.loads(source.read_text())["parameters"]
    started = time.monotonic()
    points = {}
    for coordinates in itertools.product((-1, -0.5, 0, 0.5, 1), (-1, -0.5, 0, 0.5, 1), (-1, 1), (-1, 1), (-1, 1)):
        points[coordinates] = "calibration_grid"
    for zero_axis in range(5):
        for signs in itertools.product((-1, 1), repeat=4):
            coordinates = list(signs)
            coordinates.insert(zero_axis, 0)
            points.setdefault(tuple(coordinates), "face_midpoint")
    generator = np.random.default_rng(882608)
    for coordinates in generator.uniform(-1, 1, size=(128, 5)):
        points[tuple(coordinates)] = "random_interior"
    records = []
    output_path = OUTPUT / (arguments.artifact + ".screening.json")
    for index, (coordinates, design) in enumerate(points.items()):
        parameters = perturb(base, coordinates)
        metrics = certificate_screen(parameters)["nominal"]
        record = {"index": index, "design": design, "coordinates": list(coordinates), "guard_metrics": metrics}
        if design == "random_interior" or index % 13 == 0:
            record["quick_metrics"] = quick(parameters)
        records.append(record)
        if not metrics["guard_passed"]:
            print(json.dumps({"artifact": arguments.artifact, "index": index, "coordinates": coordinates, "design": design, **metrics}), flush=True)
        if index % 32 == 0:
            output_path.write_text(json.dumps({"artifact": arguments.artifact, "runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
    output_path.write_text(json.dumps({"artifact": arguments.artifact, "runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
    chosen = []
    for key, limit in (("certificate", 1e-4), ("tail_mass", 0.02)):
        ordered = sorted(records, key=lambda record: record["guard_metrics"][key] / limit, reverse=True)
        for record in ordered[:3]:
            if record["index"] not in {item["index"] for item in chosen}:
                chosen.append(record)
    gap_records = sorted((record for record in records if "quick_metrics" in record), key=lambda record: record["quick_metrics"]["observable_gap"])
    for record in gap_records[:3]:
        if record["index"] not in {item["index"] for item in chosen}:
            chosen.append(record)
    verified = []
    for record in chosen:
        report = assess_member(perturb(base, record["coordinates"]))
        item = {"artifact": arguments.artifact, "index": record["index"], "coordinates": record["coordinates"], "design": record["design"], "assessment": report}
        verified.append(item)
        print(json.dumps({"verified": True, "artifact": arguments.artifact, "index": record["index"], "passed": report["passed"], "resolved": report["reference"]["resolved"], "gap": report["conservative_density_gap"], "certificate": report["certificate"], "tail": report["tail_mass"]}), flush=True)
        (OUTPUT / (arguments.artifact + ".verified.json")).write_text(json.dumps(verified, indent=2) + "\n")


if __name__ == "__main__":
    main()

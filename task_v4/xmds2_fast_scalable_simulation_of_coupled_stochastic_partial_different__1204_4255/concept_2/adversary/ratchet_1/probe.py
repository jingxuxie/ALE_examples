import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from simulator import quick
from search_api import assess_member


def perturbed(base, coordinates, radius):
    parameters = dict(base)
    parameters["nonlinearity"] *= 1 + radius * coordinates[0]
    parameters["duration"] *= 1 + radius * coordinates[1]
    parameters["a1"] += 0.01 * coordinates[2]
    parameters["a2"] += 0.01 * coordinates[3]
    parameters["relative_phase"] += 0.03 * coordinates[4]
    return parameters


def classify(metrics):
    failures = []
    if metrics["observable_gap"] < 0.3:
        failures.append("density_gap")
    if metrics["certificate"] > 1e-4:
        failures.append("certificate")
    if metrics["tail_mass"] > 0.02:
        failures.append("tail")
    return failures


def screen():
    started = time.monotonic()
    records = []
    generator = np.random.default_rng(282608)
    interior = generator.uniform(-0.85, 0.85, size=(16, 5)).tolist()
    (OUTPUT / "interior_coordinates.json").write_text(json.dumps(interior, indent=2) + "\n")
    for artifact in ("v_1", "v_2"):
        base = json.loads((ROOT / "attempts" / artifact / "submission.json").read_text())["parameters"]
        for radius in (0.01, 0.02, 0.03):
            points = [("corner", index, list(coordinates)) for index, coordinates in enumerate(itertools.product((-1, 1), repeat=5))]
            points += [("axis", index, (np.eye(5)[index // 2] * (-1 if index % 2 == 0 else 1)).tolist()) for index in range(10)]
            for kind, point_index, coordinates in points:
                parameters = perturbed(base, coordinates, radius)
                try:
                    metrics = quick(parameters)
                    record = {"artifact": artifact, "radius": radius, "kind": kind, "point_index": point_index, "coordinates": coordinates, "metrics": metrics, "failures": classify(metrics)}
                except (ValueError, FloatingPointError, OverflowError) as error:
                    record = {"artifact": artifact, "radius": radius, "kind": kind, "point_index": point_index, "coordinates": coordinates, "error": str(error)}
                records.append(record)
            group = [record for record in records if record["artifact"] == artifact and record["radius"] == radius]
            print(json.dumps({"artifact": artifact, "radius": radius, "screened": len(group), "failures": {name: sum(name in record.get("failures", []) for record in group) for name in ("density_gap", "certificate", "tail")}, "minimum_screen_gap": min(record.get("metrics", {}).get("observable_gap", 100) for record in group)}), flush=True)
            (OUTPUT / "screening.json").write_text(json.dumps({"runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
        for point_index, coordinates in enumerate(interior):
            metrics = quick(perturbed(base, coordinates, 0.02))
            records.append({"artifact": artifact, "radius": 0.02, "kind": "interior", "point_index": point_index, "coordinates": coordinates, "metrics": metrics, "failures": classify(metrics)})
        (OUTPUT / "screening.json").write_text(json.dumps({"runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
    return records


def verify(records):
    results = []
    for artifact in ("v_1", "v_2"):
        base = json.loads((ROOT / "attempts" / artifact / "submission.json").read_text())["parameters"]
        for radius in (0.01, 0.02, 0.03):
            group = [record for record in records if record["artifact"] == artifact and record["radius"] == radius and record["kind"] == "corner" and "metrics" in record]
            selectors = {
                "smallest_gap": lambda record: record["metrics"]["observable_gap"],
                "largest_certificate": lambda record: -record["metrics"]["certificate"],
            }
            for label, key in selectors.items():
                selected = min(group, key=key)
                report = assess_member(perturbed(base, selected["coordinates"], radius))
                result = {"artifact": artifact, "radius": radius, "selection": label, "point_index": selected["point_index"], "coordinates": selected["coordinates"], "assessment": report}
                results.append(result)
                print(json.dumps({"artifact": artifact, "radius": radius, "selection": label, "gap": report["conservative_density_gap"], "certificate": report["certificate"], "tail": report["tail_mass"], "reference_resolved": report["reference"]["resolved"], "passed": report["passed"]}), flush=True)
                (OUTPUT / "verified_failures.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    records = screen()
    verify(records)

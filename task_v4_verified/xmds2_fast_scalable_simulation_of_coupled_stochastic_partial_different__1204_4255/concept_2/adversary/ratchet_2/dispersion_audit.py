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


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from search_api import assess_member
from simulator import quick


def perturb(base, coordinates, radius):
    result = dict(base)
    result["nonlinearity"] *= 1 + 0.02 * coordinates[0]
    result["duration"] *= 1 + 0.02 * coordinates[1]
    result["a1"] += 0.01 * coordinates[2]
    result["a2"] += 0.01 * coordinates[3]
    result["relative_phase"] += 0.03 * coordinates[4]
    result["dispersion"] *= 1 + radius * coordinates[5]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", choices=("v_4", "v_3"))
    arguments = parser.parse_args()
    metadata = json.loads((ROOT / "attempts" / (arguments.artifact + ".run.json")).read_text())
    if metadata["status"] == "running":
        raise ValueError("do not inspect active attempts")
    official = json.loads((ROOT / "attempts" / (arguments.artifact + ".evaluation.json")).read_text())
    assert official["valid"] and official["passed"] and official["complete_assessment"]
    source = ROOT / "attempts" / arguments.artifact / "submission.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == official["submission_sha256"]
    base = json.loads(source.read_text())["parameters"]
    records = []
    verified = []
    started = time.monotonic()
    for radius in (0.005, 0.01):
        points = [("dispersion_axis", index, [0, 0, 0, 0, 0, sign]) for index, sign in enumerate((-1, 1))]
        points += [("six_dimensional_corner", index, list(point)) for index, point in enumerate(itertools.product((-1, 1), repeat=6))]
        for kind, index, point in points:
            metrics = quick(perturb(base, point, radius))
            record = {"artifact": arguments.artifact, "radius": radius, "kind": kind, "index": index, "coordinates": point, "metrics": metrics}
            record["failures"] = [key for key, failed in (("gap", metrics["observable_gap"] < 0.3), ("certificate", metrics["certificate"] > 1e-4), ("tail", metrics["tail_mass"] > 0.02)) if failed]
            records.append(record)
        group = [record for record in records if record["radius"] == radius]
        print(json.dumps({"artifact": arguments.artifact, "radius": radius, "count": len(group), "failure_counts": {key: sum(key in item["failures"] for item in group) for key in ("gap", "certificate", "tail")}, "axis": [item for item in group if item["kind"] == "dispersion_axis"]}), flush=True)
        (OUTPUT / (arguments.artifact + ".dispersion_screening.json")).write_text(json.dumps({"runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
        selected = [item for item in group if item["kind"] == "dispersion_axis"]
        corners = [item for item in group if item["kind"] == "six_dimensional_corner"]
        selected += [min(corners, key=lambda item: item["metrics"]["observable_gap"]), max(corners, key=lambda item: item["metrics"]["certificate"]), max(corners, key=lambda item: item["metrics"]["tail_mass"])]
        seen = set()
        for item in selected:
            identity = (item["kind"], item["index"])
            if identity in seen:
                continue
            seen.add(identity)
            report = assess_member(perturb(base, item["coordinates"], radius))
            verified.append({"artifact": arguments.artifact, "radius": radius, "kind": item["kind"], "index": item["index"], "coordinates": item["coordinates"], "assessment": report})
            print(json.dumps({"verified": True, "artifact": arguments.artifact, "radius": radius, "kind": item["kind"], "index": item["index"], "passed": report["passed"], "resolved": report["reference"]["resolved"], "gap": report["conservative_density_gap"], "certificate": report["certificate"], "tail": report["tail_mass"]}), flush=True)
            (OUTPUT / (arguments.artifact + ".dispersion_verified.json")).write_text(json.dumps(verified, indent=2) + "\n")


if __name__ == "__main__":
    main()

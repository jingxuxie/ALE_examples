import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
import math
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from search_api import assess_member
from simulator import quick


def perturb(base, point, variable, width, operation):
    result = dict(base)
    result["nonlinearity"] *= 1 + 0.02 * point[0]
    result["duration"] *= 1 + 0.02 * point[1]
    result["a1"] += 0.01 * point[2]
    result["a2"] += 0.01 * point[3]
    result["relative_phase"] += 0.03 * point[4]
    if operation == "add":
        result[variable] += width * point[5]
    else:
        result[variable] *= 1 + width * point[5]
    return result


def main():
    base = json.loads((ROOT / "champions/generation_2/submission.json").read_text())["parameters"]
    experiments = [("population", 0.005, "add"), ("population", 0.01, "add"), ("cross", 0.01, "multiply"), ("cross", 0.02, "multiply"), ("coupling", 0.02, "multiply")]
    records = []
    verified = []
    started = time.monotonic()
    for variable, width, operation in experiments:
        points = [("single_axis", index, [0, 0, 0, 0, 0, sign]) for index, sign in enumerate((-1, 1))]
        points += [("joint_corner", index, list(point)) for index, point in enumerate(itertools.product((-1, 1), repeat=6))]
        group = []
        for kind, index, point in points:
            metrics = quick(perturb(base, point, variable, width, operation))
            record = {"variable": variable, "width": width, "operation": operation, "kind": kind, "index": index, "coordinates": point, "canonical_fraction": kind == "joint_corner" and math.prod(point) == 1, "metrics": metrics}
            record["failures"] = [key for key, failed in (("gap", metrics["observable_gap"] < 0.3), ("certificate", metrics["certificate"] > 1e-4), ("tail", metrics["tail_mass"] > 0.02)) if failed]
            group.append(record)
            records.append(record)
        print(json.dumps({"variable": variable, "width": width, "screened": len(group), "failure_counts": {key: sum(key in item["failures"] for item in group) for key in ("gap", "certificate", "tail")}, "canonical_failures": sum(bool(item["failures"]) and item["canonical_fraction"] for item in group)}), flush=True)
        (OUTPUT / "preparation_screening.json").write_text(json.dumps({"runtime_seconds": time.monotonic() - started, "records": records}, indent=2) + "\n")
        selected = [item for item in group if item["kind"] == "single_axis"]
        fraction = [item for item in group if item["canonical_fraction"]]
        selected += [min(fraction, key=lambda item: item["metrics"]["observable_gap"]), max(fraction, key=lambda item: item["metrics"]["certificate"]), max(fraction, key=lambda item: item["metrics"]["tail_mass"])]
        seen = set()
        for item in selected:
            identity = (item["kind"], item["index"])
            if identity in seen:
                continue
            seen.add(identity)
            report = assess_member(perturb(base, item["coordinates"], variable, width, operation))
            verified.append({**{key: item[key] for key in ("variable", "width", "operation", "kind", "index", "coordinates", "canonical_fraction")}, "assessment": report})
            print(json.dumps({"verified": True, "variable": variable, "width": width, "kind": item["kind"], "index": item["index"], "passed": report["passed"], "resolved": report["reference"]["resolved"], "gap": report["conservative_density_gap"], "certificate": report["certificate"], "tail": report["tail_mass"]}), flush=True)
            (OUTPUT / "preparation_verified.json").write_text(json.dumps(verified, indent=2) + "\n")


if __name__ == "__main__":
    main()

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_3"
sys.path.insert(0, str(STAGE / "evaluator/hidden"))

from search_api import assess_member, parse_submission


def main():
    started = time.monotonic()
    base = parse_submission((ROOT / "champions/generation_2/submission.json").read_text())
    screening = json.loads((AUDIT / "preparation_screening.json").read_text())["records"]
    verified = json.loads((AUDIT / "preparation_verified.json").read_text())
    results = []
    for item in screening:
        if not item["failures"]:
            continue
        existing = next((entry for entry in verified if all(entry[key] == item[key] for key in ("variable", "width", "coordinates"))), None)
        if existing is not None:
            assessment = existing["assessment"]
        else:
            point = item["coordinates"]
            modified = dict(base)
            modified["nonlinearity"] *= 1 + 0.02 * point[0]
            modified["duration"] *= 1 + 0.02 * point[1]
            modified["a1"] += 0.01 * point[2]
            modified["a2"] += 0.01 * point[3]
            modified["relative_phase"] += 0.03 * point[4]
            name = item["variable"]
            if item["operation"] == "add":
                modified[name] += item["width"] * point[5]
            else:
                modified[name] *= 1 + item["width"] * point[5]
            assessment = assess_member(modified)
        results.append({"variable": item["variable"], "width": item["width"], "coordinates": item["coordinates"], "canonical_fraction": item["canonical_fraction"], "index": item["index"], "reused_audit_assessment": existing is not None, "assessment": assessment})
    result = {"full_reference_failures": results, "all_failures_resolved": all(item["assessment"]["reference"]["resolved"] and not item["assessment"]["passed"] for item in results), "runtime_seconds": time.monotonic() - started}
    assert len(results) == 3 and result["all_failures_resolved"]
    (AUDIT / "cluster_validation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"validated_failure_count": len(results), "all_failures_resolved": result["all_failures_resolved"], "runtime_seconds": result["runtime_seconds"]}), flush=True)


if __name__ == "__main__":
    main()

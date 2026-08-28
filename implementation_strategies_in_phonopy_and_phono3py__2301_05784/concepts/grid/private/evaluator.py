"""Independent scientific component scores and shared sandbox integration."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np

CONCEPT = Path(__file__).resolve().parents[1]
TARGET = CONCEPT.parents[1]


def load_shared():
    specification = importlib.util.spec_from_file_location(
        "grid_shared_evaluation", TARGET / "author" / "evaluation.py"
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def geometry_error(actual, reference, input_data):
    count = len(input_data["query_addresses"])
    offsets = np.asarray(actual["image_offsets"])
    shifts = np.asarray(actual["image_shifts"])
    distances = np.asarray(actual["distance2"])
    if offsets.dtype != np.int64 or shifts.dtype != np.int64:
        raise ValueError("Geometry integers must be int64")
    if offsets.shape != (count + 1,) or shifts.ndim != 2 or shifts.shape[1] != 3:
        raise ValueError("Invalid geometry shapes")
    if offsets[0] != 0 or offsets[-1] != len(shifts) or np.any(np.diff(offsets) < 1):
        raise ValueError("Invalid geometry CSR offsets")
    if distances.shape != (count,) or distances.dtype != np.float64:
        raise ValueError("Invalid distance array")
    if not np.isfinite(distances).all() or np.any(distances < 0):
        raise ValueError("Invalid squared distances")
    set_error = 0.0
    for query in range(count):
        found_rows = shifts[offsets[query] : offsets[query + 1]]
        if not np.array_equal(found_rows, np.unique(found_rows, axis=0)):
            raise ValueError("Image shifts must be unique and sorted")
        found = set(map(tuple, found_rows))
        start, stop = reference["image_offsets"][query : query + 2]
        wanted = set(map(tuple, reference["image_shifts"][start:stop]))
        set_error += 1 - len(found & wanted) / len(found | wanted)
    scale = max(float(np.sqrt(np.mean(reference["distance2"] ** 2))), 1e-12)
    distance_error = float(np.sqrt(np.mean((distances - reference["distance2"]) ** 2))) / scale
    return 0.5 * (set_error / count + distance_error)


def spectral_error(actual, reference, input_data):
    expected = (len(input_data["sampling_points"]), input_data["frequencies"].shape[1])
    errors = []
    span = max(float(np.ptp(input_data["sampling_points"])), 1.0)
    for field in ("dos", "cumulative"):
        values = np.asarray(actual[field])
        if values.shape != expected or values.dtype != np.float64 or not np.isfinite(values).all():
            raise ValueError("Invalid " + field + " array")
        floor = 1e-3 / span if field == "dos" else 1e-6
        scales = np.maximum(np.sqrt(np.mean(reference[field] ** 2, axis=0)), floor)
        errors.append(float(np.mean(np.sqrt(np.mean((values - reference[field]) ** 2, axis=0)) / scales)))
    return float(np.mean(errors))


def score_case(actual, reference, baseline, case, input_data):
    result = {}
    for name, error_function in (("geometry", geometry_error), ("spectral", spectral_error)):
        baseline_error = error_function(baseline, reference, input_data)
        denominator = max(baseline_error, 1e-8)
        try:
            error = error_function(actual, reference, input_data)
            if not np.isfinite(error):
                raise ValueError("Nonfinite error")
            result[name] = {"score": 1 / (1 + error / denominator), "error": error,
                            "baseline_error": baseline_error}
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as failure:
            result[name] = {"score": 0.0, "error": None, "baseline_error": baseline_error,
                            "invalid": str(failure)}
    return result


def summarize_resources(report, manifest):
    lookup = {case["id"]: case for case in manifest}
    families = {}
    for result in report["cases"]:
        case = lookup[result["id"]]
        metrics = json.loads((CONCEPT / "private" / case["baseline_metrics"]).read_text())
        success = result["status"] == "ok"
        seconds = max(float(result["seconds"]), 1e-6)
        rss = max(float(result.get("max_rss_kb") or case["memory_mb"] * 1024), 1)
        speedup = metrics["seconds"] / seconds if success else 0.0
        memory_ratio = metrics["max_rss_kb"] / rss if success else 0.0
        result["baseline_seconds"] = metrics["seconds"]
        result["baseline_max_rss_kb"] = metrics["max_rss_kb"]
        result["speedup"] = speedup
        result["memory_ratio"] = memory_ratio
        families.setdefault(result["family"], []).append(result)
    summaries = {}
    for family, results in families.items():
        summaries[family] = {
            "geometry": float(np.mean([item["components"]["geometry"]["score"] for item in results])),
            "spectral": float(np.mean([item["components"]["spectral"]["score"] for item in results])),
            "core": float(np.mean([item["core_score"] for item in results])),
            "seconds": float(np.mean([item["seconds"] for item in results])),
            "peak_rss_kb": max(item.get("max_rss_kb") or 0 for item in results),
            "speedup": float(np.mean([item["speedup"] for item in results])),
            "memory_ratio": float(np.mean([item["memory_ratio"] for item in results])),
        }
    report["grid_summary"] = {
        "families": summaries,
        "family_balanced_core": float(np.mean([item["core"] for item in summaries.values()])),
        "worst_family_core": min(item["core"] for item in summaries.values()),
        "mean_seconds": float(np.mean([item["seconds"] for item in report["cases"]])),
        "worst_family_seconds": max(item["seconds"] for item in summaries.values()),
        "mean_peak_rss_kb": float(np.mean([item.get("max_rss_kb") or 0 for item in report["cases"]])),
        "worst_family_peak_rss_kb": max(item["peak_rss_kb"] for item in summaries.values()),
        "worst_family_speedup": min(item["speedup"] for item in summaries.values()),
        "worst_family_memory_ratio": min(item["memory_ratio"] for item in summaries.values()),
        "score": 0.5 * (float(np.mean([item["core"] for item in summaries.values()]))
                        + min(item["core"] for item in summaries.values())),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--split", default="pool")
    parser.add_argument("--output", "--report", type=Path, default=CONCEPT / "private/reference/evaluation.json")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--stored-reference", action="store_true")
    args = parser.parse_args()
    report = load_shared().evaluate(CONCEPT, args.submission, args.split, args.output,
                                    score_case=score_case, case_ids=args.case_ids,
                                    stored_reference=args.stored_reference)
    report["score_definition"] = "Independent geometry/spectral quality 1/(1+error/max(baseline_error,1e-8)); baseline .5, explicit 1e-8 floor for baseline-exact components; family mean and minimum; measured resources reported separately."
    if not args.stored_reference:
        manifest = json.loads((CONCEPT / "private/challenge_pool/manifest.json").read_text())
        summarize_resources(report, manifest)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

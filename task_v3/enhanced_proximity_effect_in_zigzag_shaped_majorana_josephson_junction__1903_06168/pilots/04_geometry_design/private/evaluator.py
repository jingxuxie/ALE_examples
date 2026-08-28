"""Score geometry files using private, full-scale physical calculations."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

PRIVATE = Path(__file__).resolve().parent
SCORING_RULE = "unbounded-weak-to-strong-v1"
sys.path.insert(0, str(PRIVATE / "reference"))
from physics import ForwardModel, feasibility, geometry_arrays, geometry_digest, load_result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def fingerprint(request, scenarios, strong):
    digest = hashlib.sha256()
    digest.update(b"geometry-physical-measurements-v1")
    digest.update((PRIVATE / "reference" / "physics.py").read_bytes())
    digest.update(inspect.getsource(measure_job).encode())
    digest.update(json.dumps([request, scenarios], sort_keys=True).encode())
    digest.update(geometry_digest(strong).encode())
    return digest.hexdigest()


def measure_job(job):
    request, geometry, scenario, points = job
    masks = geometry_arrays(request, geometry)
    started = time.monotonic()
    model = ForwardModel(request, masks, scenario)
    invariant = model.topological_invariant()
    spectrum = model.spectral_gap(np.linspace(0, math.pi, points))
    return {"scenario": scenario, "class_d_invariant": invariant, "dimension": model.dimension, "seconds": time.monotonic() - started, **spectrum}


def observations(request, masks, scenarios, points, workers):
    encoded = {name: mask.astype(int).tolist() for name, mask in masks.items()}
    jobs = [(request, encoded, scenario, points) for scenario in scenarios]
    if workers == 1:
        return [measure_job(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(measure_job, jobs))


def performance(measurements):
    gaps = np.asarray([row["gap_mev"] for row in measurements])
    valid = all(row["class_d_invariant"] == -1 for row in measurements) and bool(np.all(gaps > 1e-5))
    robust_gap = 0.5 * float(gaps.mean()) + 0.5 * float(gaps.min())
    return {"physical_feasibility": valid, "robust_gap_mev": robust_gap, "mean_gap_mev": float(gaps.mean()), "worst_gap_mev": float(gaps.min())}


def normalized_score(value, weak, strong):
    if not all(math.isfinite(number) for number in (value, weak, strong)) or strong <= weak + 1e-4:
        raise ValueError("Unusable weak-to-strong physical calibration")
    return float((value - weak) / (strong - weak))


def summarize_scores(records):
    core_score = float(np.mean([record["score"] for record in records]))
    worst = min(records, key=lambda record: record["score"])
    return {
        "score": core_score,
        "core_score": core_score,
        "core_feasibility": float(np.mean([record["core_feasible"] for record in records])),
        "worst_family_score": worst["score"],
        "worst_family": worst["request_id"],
    }


def calibrate(case_directory, workers, points=51):
    request = read_json(case_directory / "request.json")
    scenarios = read_json(case_directory / "scenarios.json")
    request_id = request["request_id"]
    strong = load_result(request, PRIVATE / "reference" / f"{request_id}.json")
    weak = geometry_arrays(request, request["baseline_geometry"])
    calibration_path = PRIVATE / "reference" / f"{request_id}_calibration.json"
    expected = fingerprint(request, scenarios, strong)
    cached = read_json(calibration_path) if calibration_path.exists() else {}
    if cached.get("fingerprint") == expected and cached.get("momentum_points") == points and cached.get("ready") and cached.get("scoring_rule") == SCORING_RULE:
        return cached
    record = {"request_id": request_id, "fingerprint": expected, "momentum_points": points, "scoring_rule": SCORING_RULE, "ready": False}
    for label, masks in (("weak", weak), ("strong", strong)):
        geometry_status = feasibility(request, masks)
        if not geometry_status["valid"]:
            raise ValueError(f"{label} geometry infeasible: {geometry_status}")
        checkpoint = PRIVATE / "reference" / f"{request_id}_{label}_measurements.json"
        previous = read_json(checkpoint) if checkpoint.exists() else {}
        if previous.get("fingerprint") == expected and previous.get("momentum_points") == points:
            rows = previous["measurements"]
        else:
            print(f"Measuring {request_id} {label}: {len(scenarios)} scenarios x {points} momenta", flush=True)
            rows = observations(request, masks, scenarios, points, workers)
            write_json(checkpoint, {"fingerprint": expected, "momentum_points": points, "measurements": rows})
        record[label] = {"geometry": geometry_status, "measurements": rows, **performance(rows)}
    if not record["strong"]["physical_feasibility"] or not record["weak"]["physical_feasibility"]:
        write_json(calibration_path, record)
        raise ValueError(f"{request_id}: a physical anchor is not topological at all held-out points")
    weak_gap, strong_gap = record["weak"]["robust_gap_mev"], record["strong"]["robust_gap_mev"]
    normalized_score(strong_gap, weak_gap, strong_gap)
    record["ready"] = points == 51
    record["anchor_scores"] = {"weak": normalized_score(weak_gap, weak_gap, strong_gap), "strong": normalized_score(strong_gap, weak_gap, strong_gap)}
    write_json(calibration_path, record)
    print(request_id, "weak=", weak_gap, "strong=", strong_gap, "ready=", record["ready"], flush=True)
    return record


def score_case(case_directory, results_directory, workers):
    request = read_json(case_directory / "request.json")
    request_id = request["request_id"]
    scenarios = read_json(case_directory / "scenarios.json")
    strong = load_result(request, PRIVATE / "reference" / f"{request_id}.json")
    calibration = read_json(PRIVATE / "reference" / f"{request_id}_calibration.json")
    if not calibration.get("ready") or calibration["fingerprint"] != fingerprint(request, scenarios, strong) or calibration.get("scoring_rule") != SCORING_RULE:
        raise RuntimeError(f"{request_id}: missing/stale full-resolution physical calibration")
    record = {"request_id": request_id, "score": 0.0, "core_feasible": False}
    try:
        path = results_directory / f"{request_id}.json"
        if path.stat().st_size > 2_000_000:
            raise ValueError("result exceeds 2 MB")
        masks = load_result(request, path)
        record["geometry"] = feasibility(request, masks)
        if not record["geometry"]["valid"]:
            return record
        measured = observations(request, masks, scenarios, 51, workers)
        record["measurements"] = measured
        record.update(performance(measured))
        if record["physical_feasibility"]:
            record["core_feasible"] = True
            weak_gap, strong_gap = calibration["weak"]["robust_gap_mev"], calibration["strong"]["robust_gap_mev"]
            record["score"] = normalized_score(record["robust_gap_mev"], weak_gap, strong_gap)
            record["unclipped_gain"] = (record["robust_gap_mev"] - weak_gap) / (strong_gap - weak_gap)
    except (ValueError, TypeError, OSError, KeyError, RuntimeError, RecursionError, np.linalg.LinAlgError) as error:
        record["failure"] = f"{type(error).__name__}: {error}"
    return record


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--calibrate", action="store_true")
    mode.add_argument("--results-dir", type=Path)
    mode.add_argument("--export-requests", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if not 1 <= arguments.workers <= 8:
        parser.error("workers must be between 1 and 8")
    cases = sorted((PRIVATE / "challenge_pool").iterdir())
    cases = [directory for directory in cases if directory.is_dir() and (arguments.case is None or directory.name == arguments.case)]
    if not cases:
        parser.error("no matching challenge")
    records = []
    for case_directory in cases:
        if arguments.export_requests is not None:
            request = read_json(case_directory / "request.json")
            write_json(arguments.export_requests / f"{request['request_id']}.json", request)
            records.append({"request_id": request["request_id"]})
        elif arguments.calibrate:
            records.append(calibrate(case_directory, arguments.workers))
        else:
            records.append(score_case(case_directory, arguments.results_dir, arguments.workers))
        write_json(arguments.output, {"complete": False, "cases": records})
    result = {"complete": True, "scoring_rule": SCORING_RULE, "cases": records}
    if arguments.results_dir is not None:
        result.update(summarize_scores(records))
    write_json(arguments.output, result)


if __name__ == "__main__":
    main()

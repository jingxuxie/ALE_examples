import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilots/04_geometry_design"


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-seconds", type=float, default=1800)
    parser.add_argument("--audit", choices=("scale_research", "highfield_research"), default="scale_research")
    arguments = parser.parse_args()
    directory = PILOT / "private" / arguments.audit
    deadline = time.monotonic() + arguments.wait_seconds
    execution_path = directory / "run/execution.json"
    calibration_path = directory / "reference/calibration.json"
    while not execution_path.exists() or not calibration_path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("Scale audit execution or calibration is incomplete; no hardness score assigned")
        time.sleep(5)
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[28:40])
    specification = importlib.util.spec_from_file_location("geometry_audit_evaluator", PILOT / "private/evaluator.py")
    evaluator = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = evaluator
    specification.loader.exec_module(evaluator)
    request = read(directory / "request.json")
    calibration = read(calibration_path)
    execution = read(execution_path)
    result = directory / "run/results" / f"{request['request_id']}.json"
    masks = evaluator.load_result(request, result)
    report = {
        "scope": read(directory / "provenance.json")["scope_note"],
        "execution": execution,
        "geometry": evaluator.feasibility(request, masks),
        "score": None,
    }
    if report["geometry"]["valid"]:
        observations = evaluator.observations(request, masks, read(directory / "scenarios.json"), 51, 3)
        report.update(measurements=observations, **evaluator.performance(observations))
        weak, strong = calibration["weak"], calibration["strong"]
        report.update(weak_robust_gap_mev=weak["robust_gap_mev"], strong_robust_gap_mev=strong["robust_gap_mev"])
        if report["physical_feasibility"] and weak["physical_feasibility"] and strong["physical_feasibility"]:
            report["score"] = evaluator.normalized_score(report["robust_gap_mev"], weak["robust_gap_mev"], strong["robust_gap_mev"])
    evaluator.write_json(directory / "submission_score.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "measurements"}, indent=2), flush=True)


if __name__ == "__main__":
    main()

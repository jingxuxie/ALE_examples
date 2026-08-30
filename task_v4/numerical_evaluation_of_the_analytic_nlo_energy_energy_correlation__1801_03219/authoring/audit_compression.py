import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
sys.path.insert(0, str(CONCEPT / "participant" / "workspace"))
from model import bin_average, evaluate, load_model


def main():
    directory = CONCEPT / "adversary" / "evaluator_audit"
    directory.mkdir(parents=True, exist_ok=True)
    reports = {}
    for name, artifact in {
        "zero": {"knots": [-24,24], "coefficients": [[[0],[0],[0]]]},
        "nonfinite": {"knots": [-24,24], "coefficients": [[[float("nan")],[0],[0]]]},
        "bad_span": {"knots": [-23,24], "coefficients": [[[0],[0],[0]]]},
        "unsorted": {"knots": [-24,0,-1,24], "coefficients": [[[0],[0],[0]]]*3},
        "oversized": {"knots": [-24,-8,8,24], "coefficients": [[[0]*65]*3]*3},
        "wrong_channels": {"knots": [-24,24], "coefficients": [[[0],[0]]]},
    }.items():
        path = directory / (name+".json")
        path.write_text(json.dumps(artifact))
        try:
            result = load_model(path)
            reports[name] = {"accepted": True, "scalar_count": result["scalar_count"]}
        except Exception as exception:
            reports[name] = {"accepted": False, "reason": str(exception)}
    analytic = {"knots": np.array([-24.0,24.0]),
                "coefficients": [[np.array([3.0,2.0,4.0]), np.array([2.0]), np.array([0.0,1.0])]]}
    coordinates = np.linspace(-24,24,100)
    transformed = coordinates/24
    exact = np.column_stack((8*transformed**2+2*transformed-1,
                             np.full_like(transformed,2), transformed))
    exact_derivative = np.column_stack(((16*transformed+2)/24,
                                        np.zeros_like(transformed), np.full_like(transformed,1/24)))
    reports["polynomial_values_max_error"] = float(np.max(np.abs(evaluate(analytic,coordinates)-exact)))
    reports["polynomial_derivatives_max_error"] = float(np.max(np.abs(evaluate(analytic,coordinates,True)-exact_derivative)))
    reports["polynomial_full_bin_error"] = float(np.max(np.abs(bin_average(analytic,-24,24)-[5/3,2,0])))
    assert reports["zero"]["accepted"]
    assert all(not reports[name]["accepted"] for name in ["nonfinite","bad_span","unsorted","oversized","wrong_channels"])
    assert reports["polynomial_values_max_error"] < 1e-12
    assert reports["polynomial_derivatives_max_error"] < 1e-12
    assert reports["polynomial_full_bin_error"] < 1e-12
    specification = importlib.util.spec_from_file_location("compression_grader", CONCEPT/"evaluator"/"evaluate.py")
    grader = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(grader)
    baseline = grader.grade(CONCEPT/"participant"/"baseline")
    assert not baseline["passed"]
    assert baseline["max_tolerance_ratio"] > 100
    reports["baseline_rejected_by_quality"] = True
    (CONCEPT/"evaluator"/"hidden"/"target.json").write_text(json.dumps({
        "generation": 1, "frozen_before_attempt": True,
        "scalar_budget": 320, "max_tolerance_ratio": 1.0,
        "minimum_baseline_improvement": 100,
        "baseline_max_tolerance_ratio": baseline["max_tolerance_ratio"],
        "point_and_bin_mixed_tolerance": 2e-8, "derivative_mixed_tolerance": 2e-7,
    }, indent=2)+"\n")
    baseline = grader.grade(CONCEPT/"participant"/"baseline")
    (CONCEPT/"adversary"/"baseline_score.json").write_text(json.dumps(baseline,indent=2)+"\n")
    (directory/"audit.json").write_text(json.dumps(reports,indent=2)+"\n")
    (CONCEPT/"status.json").write_text(json.dumps({
        "concept": "compact_color_resolved_response", "mode": "A", "generation": 1,
        "status": "ready", "baseline": baseline, "target_frozen": True,
        "solvability": "unknown", "evaluator_validated": True,
    },indent=2)+"\n")
    print(json.dumps({"audit": reports, "baseline": baseline},indent=2))


if __name__ == "__main__":
    main()

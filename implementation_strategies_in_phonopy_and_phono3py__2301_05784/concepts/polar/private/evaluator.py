"""Independent component scoring; execution is delegated to the common harness."""

import importlib.util
from pathlib import Path

import numpy as np


PRIVATE = Path(__file__).resolve().parent
POLAR = PRIVATE.parent


def arrays(value):
    if isinstance(value, (str, Path)):
        with np.load(value, allow_pickle=False) as archive:
            return dict(archive)
    return value


def relative_error(actual, expected):
    if actual.shape != expected.shape or not np.all(np.isfinite(actual)):
        return 1e30
    difference = (actual - expected).reshape(len(expected), -1)
    denominator = np.maximum(np.linalg.norm(expected.reshape(len(expected), -1), axis=1), 1e-10)
    return float(np.sqrt(np.mean((np.linalg.norm(difference, axis=1) / denominator) ** 2)))


def errors(actual, reference, input_data):
    actual, reference, input_data = arrays(actual), arrays(reference), arrays(input_data)
    modes = 3 * len(input_data["masses"])
    packets = len(input_data["response_groups"])
    directions = len(input_data["response_directions"])
    shapes = {
        "derivative": (len(input_data["q_cart"]), 3, modes, modes),
        "response": (packets, 3, modes, modes),
        "velocity": (packets, directions, modes),
        "branch_velocity": (packets, directions, modes, 3),
    }
    result = {}
    for key, shape in shapes.items():
        candidate = np.asarray(actual.get(key, []))
        dtype = np.complex128 if key in ("derivative", "response") else np.float64
        result[key] = relative_error(candidate, reference[key]) if candidate.shape == shape and candidate.dtype == dtype else 1e30
    result["polar_derivative"] = result["derivative"]
    result["mode_response"] = float(np.linalg.norm([result[key] for key in ("response", "velocity", "branch_velocity")]) / np.sqrt(3))
    return result


def score_details(actual, reference, baseline, case, input_data):
    """Accept NPZ paths or array mappings without executing a submission."""
    actual_errors = errors(actual, reference, input_data)
    baseline_errors = errors(baseline, reference, input_data)
    reference_errors = case.get("reference_errors", {})
    scores = {}
    for component in ("polar_derivative", "mode_response"):
        scientific_floor = 1e-5 if component == "polar_derivative" else 1e-6
        scale = max(baseline_errors[component], case.get("error_floor", 1e-10), scientific_floor)
        scores[component] = 1 / (1 + actual_errors[component] / scale)
    return {"score": float(np.mean(list(scores.values()))), "component_scores": scores,
            "errors": actual_errors, "baseline_errors": baseline_errors, "reference_errors": reference_errors}


def score_case(actual, reference, baseline, case, input_data):
    """Return exactly two component records, compatible with author/evaluation.py."""
    details = score_details(actual, reference, baseline, case, input_data)
    return {
        component: {"score": details["component_scores"][component],
                    "error": details["errors"][component],
                    "baseline_error": details["baseline_errors"][component],
                    "reference_error": details["reference_errors"].get(component, 0.0),
                    "raw_errors": {key: details["errors"][key] for key in keys}}
        for component, keys in (("polar_derivative", ("derivative",)),
                                ("mode_response", ("response", "velocity", "branch_velocity")))
    }


def main():
    import sys

    helper_path = POLAR.parents[1] / "author/evaluation.py"
    spec = importlib.util.spec_from_file_location("common_evaluation", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if not any(argument in ("--output", "--report") for argument in sys.argv):
        sys.argv.extend(["--output", str(POLAR / "private/reference/evaluation.json")])
    helper.cli(concept=POLAR, score_case=score_case)


if __name__ == "__main__":
    main()

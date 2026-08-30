import argparse
import hashlib
import json
from pathlib import Path
import time

from design_common import aggregate, load_case, read_design, score_case


ROOT = Path(__file__).resolve().parent


def _evaluate(artifact):
    axes = read_design(artifact)
    protocol = json.loads((ROOT / "protocol.json").read_text())
    for relative, expected in protocol["sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("trusted evaluator asset hash mismatch")
    supports = json.loads((ROOT / "hidden" / "supports.json").read_text())
    results = {}
    for identifier in protocol["cases"]:
        case = load_case(ROOT / "hidden" / (identifier + ".json.gz"))
        results[identifier] = score_case(case, supports[identifier], axes)
    result = aggregate(results)
    result["valid"] = True
    result["improvement_over_baseline"] = result["correctness_fraction"] - protocol["baseline_fraction"]
    result["passed"] = result["correctness_fraction"] >= protocol["target_fraction"] and all(group["fraction"] >= protocol["group_floors"][identifier] for identifier, group in result["groups"].items())
    result["target_fraction"] = protocol["target_fraction"]
    result["mode"] = "C"
    result["reason"] = "target and all group floors met" if result["passed"] else "overall target or at least one group floor not met"
    result["score"] = result["core_score"]
    return result


def evaluate(artifact):
    started = time.monotonic()
    try:
        result = _evaluate(artifact)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, RecursionError) as error:
        result = {"valid": False, "passed": False, "score": 0.0, "core_score": 0.0, "worst_family_score": 0.0, "correctness_fraction": 0.0, "worst_group_fraction": 0.0, "reason": str(error), "mode": "C"}
    result["runtime_seconds"] = time.monotonic() - started
    result["runtime_score"] = float(result["valid"])
    result["resource_score"] = float(result["valid"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", nargs="?", type=Path)
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    artifact = arguments.submission or arguments.artifact
    if artifact is None:
        parser.error("provide a JSON artifact path or --submission PATH")
    result = evaluate(artifact)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()

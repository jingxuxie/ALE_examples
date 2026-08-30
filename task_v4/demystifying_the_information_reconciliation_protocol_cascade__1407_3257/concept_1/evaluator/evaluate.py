import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy")
    parser.add_argument("--split", choices=["train", "dev", "hidden"], default="hidden")
    parser.add_argument("--output", required=True)
    parser.add_argument("--jobs", type=int, choices=range(1, 17), default=4)
    arguments = parser.parse_args()
    started = time.monotonic()
    try:
        result = evaluate(arguments)
    except Exception as error:
        result = {"split": arguments.split, "core_score": 0.0, "worst_family_score": 0.0,
                  "runtime_resource_score": 0.0, "valid": False, "passed": False,
                  "target_pass": False, "reliability_pass": False,
                  "reason": f"invalid_evaluation:{type(error).__name__}", "error": str(error)[:240]}
    result["elapsed_seconds"] = time.monotonic() - started
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    Path(arguments.output).write_text(text)
    print(json.dumps({name: result[name] for name in ["split", "core_score", "worst_family_score", "runtime_resource_score", "valid", "passed", "reason"]}))


def evaluate(arguments):
    manifest_path = ROOT / "evaluator" / "frozen.json"
    if not manifest_path.is_file():
        raise RuntimeError("reference has not been frozen")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for relative, expected in manifest["sha256"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"trusted input changed after freeze: {relative}")
    sys.path.insert(0, str(ROOT / "participant"))
    from cascade_sim import load_policy
    from scoring import evaluate_suite
    if not arguments.policy:
        raise ValueError("missing --policy")
    policy_path = Path(arguments.policy).resolve()
    suite_path = ROOT / ("evaluator/hidden/cases.json" if arguments.split == "hidden" else f"participant/inputs/{arguments.split}.json")
    suite = json.loads(suite_path.read_text())
    policy, policy_digest = load_policy(policy_path, with_digest=True)
    result = evaluate_suite(policy, suite, jobs=arguments.jobs)
    result.pop("case_results")
    result["policy_sha256"] = policy_digest
    result["suite_sha256"] = hashlib.sha256(suite_path.read_bytes()).hexdigest()
    result["frozen"] = manifest_path.exists()
    return result


if __name__ == "__main__":
    main()

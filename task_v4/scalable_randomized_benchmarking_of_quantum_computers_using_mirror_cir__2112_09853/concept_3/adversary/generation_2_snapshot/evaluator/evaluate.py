import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hidden"))
from core import (InvalidSubmission, circuit_weights, load_json,
                  score_metrics, summarize, validate_submission)
from faults import omission_profile


def evaluate(submission):
    started = time.perf_counter()
    report = {"valid": False, "passed": False, "core_score": 0.0,
              "worst_family": None, "worst_family_score": 0.0,
              "resource_score": 0.0, "runtime_score": 0.0,
              "runtime": 0.0, "runtime_seconds": 0.0, "reason": "not evaluated",
              "families": {}}
    try:
        spec_path = Path(__file__).resolve().parent / "hidden" / "frozen_spec.json"
        spec, spec_hash = load_json(spec_path)
        artifact, artifact_hash = load_json(submission)
        report.update(spec_sha256=spec_hash, artifact_sha256=artifact_hash)
        report["generation"] = spec["generation"]
        report["ratchet_generations"] = spec["ratchet_generations"]
        circuits = validate_submission(artifact, spec)
        report["valid"] = True
        report["resource_score"] = 1.0
        for family in spec["families"]:
            circuit = circuits[family["id"]]
            resources = {
                "qubits": family["n"], "rounds": len(circuit["layers"]),
                "cx_count": sum(len(layer["cx"]) for layer in circuit["layers"]),
                "h_count": sum(word.count("H") for layer in circuit["layers"] for word in layer["local"]),
                "s_count": sum(word.count("S") for layer in circuit["layers"] for word in layer["local"]),
                "cx_depth": sum(bool(layer["cx"]) for layer in circuit["layers"]),
                "primitive_depth": sum(max(len(word.replace("I", "")) for word in layer["local"]) + bool(layer["cx"]) for layer in circuit["layers"]),
                "max_rounds": family["max_rounds"], "max_cx": family["max_cx"],
                "round_utilization": len(circuit["layers"]) / family["max_rounds"],
                "cx_utilization": sum(len(layer["cx"]) for layer in circuit["layers"]) / family["max_cx"],
            }
            metrics = summarize(family["n"], circuit_weights(family["n"], circuit["layers"]))
            ideal_score, failed = score_metrics(metrics, family["targets"])
            faults = omission_profile(family["n"], circuit["layers"],
                                      spec["robustness"]["max_omissions"], spec["robustness"]["minimum_weight"])
            score = min(ideal_score, faults["core_score"])
            failed.extend("fault_robustness." + name + ".minimum"
                          for name, count in faults["failed_scenario_counts"].items() if count)
            report["families"][family["id"]] = {
                "core_score": score, "passed": not failed, "failed_objectives": failed,
                "ideal_score": ideal_score, "robustness_score": faults["core_score"],
                "metrics": metrics, "targets": family["targets"],
                "resources": resources, "resource_score": 1.0,
                "rounds": len(circuit["layers"]),
                "cx_count": sum(len(layer["cx"]) for layer in circuit["layers"]),
                "fault_robustness": faults,
                "one_dropped_cx": {"scenarios": faults["by_omission_count"]["1"]["scenarios"],
                                   "minimum": faults["by_omission_count"]["1"]["minimum"], "affects_pass": True},
            }
        worst = min(report["families"], key=lambda name: report["families"][name]["core_score"])
        report["worst_family"] = worst
        report["core_score"] = report["families"][worst]["core_score"]
        report["worst_family_score"] = report["core_score"]
        report["resources"] = {
            key: sum(value["resources"][key] for value in report["families"].values())
            for key in ("rounds", "cx_count", "h_count", "s_count")
        }
        report["resources"]["max_primitive_depth"] = max(value["resources"]["primitive_depth"] for value in report["families"].values())
        report["passed"] = all(value["passed"] for value in report["families"].values())
        report["reason"] = "all ideal and up-to-two-omission spreading targets met" if report["passed"] else "unmet ideal or omission-robustness targets; see failed_objectives"
    except (InvalidSubmission, OSError, ValueError, TypeError, RecursionError) as error:
        report.update(valid=False, passed=False, core_score=0.0, worst_family_score=0.0,
                      resource_score=0.0, reason=str(error))
    report["runtime"] = time.perf_counter() - started
    report["runtime_seconds"] = report["runtime"]
    report["runtime_score"] = 1.0 / (1.0 + report["runtime_seconds"])
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate static native Clifford circuits; never executes submission code.")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = evaluate(args.submission)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(serialized)
    print(serialized, end="")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

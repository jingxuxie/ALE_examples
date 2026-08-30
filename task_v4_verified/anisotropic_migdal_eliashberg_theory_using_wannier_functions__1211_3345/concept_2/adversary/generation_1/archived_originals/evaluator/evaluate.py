import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
from _physics import EliashbergSolver, constraint_report, json_write, load_instance, physics_report, read_artifact
from _audit import independent_audit


def evaluate(artifact, output, audit_output):
    started = time.monotonic()
    instance = load_instance(ROOT / "evaluator" / "hidden" / "frozen_input")
    result = {
        "schema_version": 1, "admissible": False, "valid": False, "score": 0.0,
        "target_ratio": instance["config"]["target_ratio"], "target_met": False,
        "input_sha256": instance["input_sha256"],
    }
    audit = {"schema_version": 1, "passed": False, "input_sha256": instance["input_sha256"]}
    try:
        kernels, digest = read_artifact(artifact, instance["config"], with_digest=True)
        result["artifact_sha256"] = digest
        constraints, canonical = constraint_report(kernels, instance)
        result["admissible"] = constraints["admissible"]
        audit["constraints"] = constraints
        if result["admissible"]:
            physics = physics_report(canonical, instance)
            independent = independent_audit(canonical, instance, physics, EliashbergSolver)
            audit["physics"] = physics
            audit["independent"] = independent
            audit["passed"] = physics["converged"] and independent["passed"]
            result["score"] = physics["score"]
            result["target_met"] = physics["target_met"]
            result["converged"] = physics["converged"]
            result["independent_audit_passed"] = independent["passed"]
            result["valid"] = result["target_met"] and audit["passed"]
        else:
            result["error"] = "; ".join(constraints["errors"])
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        audit["error"] = result["error"]
    result["elapsed_seconds"] = time.monotonic() - started
    result["audit_file"] = str(Path(audit_output).resolve())
    audit["result"] = result
    json_write(audit_output, audit)
    json_write(output, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_positional", nargs="?", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", "--result", type=Path, default=Path("evaluation.json"))
    parser.add_argument("--audit-output", type=Path)
    arguments = parser.parse_args()
    artifact = arguments.artifact or arguments.artifact_positional
    if artifact is None:
        parser.error("provide an artifact path")
    audit_output = arguments.audit_output or arguments.output.with_name(arguments.output.stem + ".audit.json")
    result = evaluate(artifact, arguments.output, audit_output)
    print(result)


if __name__ == "__main__":
    main()

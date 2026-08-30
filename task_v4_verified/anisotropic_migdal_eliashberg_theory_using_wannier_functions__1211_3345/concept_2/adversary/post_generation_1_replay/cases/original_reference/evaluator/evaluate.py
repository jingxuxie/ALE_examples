import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import json
import resource
import time
from pathlib import Path

from _audit import independent_audit
from _physics import EliashbergSolver, constraint_report, json_write, load_instance, physics_report, read_artifact
from reporting import add_reporting_fields


EVALUATOR = Path(__file__).resolve().parent


def evaluate(artifact, output, audit_output):
    started_wall = time.monotonic()
    started_cpu = time.process_time()
    result = {"schema_version": 2, "admissible": False, "valid": False, "score": 0., "target_met": False}
    audit = {"schema_version": 2, "passed": False}
    try:
        instance = load_instance(EVALUATOR / "hidden" / "frozen_input")
        result["input_sha256"] = instance["input_sha256"]
        result["target_ratio"] = instance["config"]["target_ratio"]
        audit["input_sha256"] = instance["input_sha256"]
        kernels, digest = read_artifact(artifact, instance["config"], with_digest=True)
        result["artifact_sha256"] = digest
        constraints, canonical = constraint_report(kernels, instance)
        result["admissible"] = constraints["admissible"]
        audit["constraints"] = constraints
        if not result["admissible"]:
            result["error"] = "; ".join(constraints["errors"])
        else:
            physics = physics_report(canonical, instance)
            independent = independent_audit(canonical, instance, physics, EliashbergSolver)
            audit["physics"] = physics
            audit["independent"] = independent
            audit["passed"] = physics["converged"] and independent["passed"]
            result.update(score=physics["score"], target_met=physics["target_met"], converged=physics["converged"],
                          independent_audit_passed=independent["passed"], valid=physics["target_met"] and audit["passed"])
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        audit["error"] = result["error"]
    elapsed = time.monotonic() - started_wall
    result["elapsed_seconds"] = elapsed
    result["audit_file"] = str(Path(audit_output).resolve())
    result = add_reporting_fields(result, {
        "wall_seconds": elapsed,
        "cpu_seconds": time.process_time() - started_cpu,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "measurement_scope": "Evaluator process only; elapsed/CPU cover evaluate(), Linux peak RSS is process lifetime. No candidate code executes.",
    })
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
    print(json.dumps(evaluate(artifact, arguments.output, audit_output), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

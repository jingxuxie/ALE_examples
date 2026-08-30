import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
from pathlib import Path

from physics import constraint_report, json_write, load_instance, physics_report, read_artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, default=Path("public_check.json"))
    parser.add_argument("--constraints-only", action="store_true")
    arguments = parser.parse_args()
    instance = load_instance()
    result = {"admissible": False, "valid": False, "score": 0.0, "independent_audit": "not_run"}
    try:
        kernels = read_artifact(arguments.artifact, instance["config"])
        constraints, canonical = constraint_report(kernels, instance)
        result["constraints"] = constraints
        result["admissible"] = constraints["admissible"]
        if result["admissible"] and not arguments.constraints_only:
            result["physics"] = physics_report(canonical, instance)
            result["score"] = result["physics"]["score"]
            result["public_pass"] = result["physics"]["target_met"] and result["physics"]["converged"]
    except Exception as error:
        result["error"] = str(error)
    result["input_sha256"] = instance["input_sha256"]
    json_write(arguments.output, result)
    print(result)


if __name__ == "__main__":
    main()

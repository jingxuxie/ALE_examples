import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


HIDDEN = Path(__file__).resolve().parent / "hidden"
SPEC = json.loads((HIDDEN / "assay_spec.json").read_text())


def evaluate(witness):
    started = time.perf_counter()
    environment = os.environ.copy()
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        environment[variable] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    try:
        process = subprocess.run([sys.executable, "-I", "-B", str(HIDDEN / "assay_worker.py"), os.path.abspath(witness)], cwd=HIDDEN, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment, timeout=SPEC["evaluator_wall_seconds"], check=False)
        if process.returncode:
            report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, resource_score=0.0, reason="validator failed or exceeded resource limit")
        else:
            report = json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, resource_score=0.0, reason="validator wall-time limit exceeded")
    except (OSError, ValueError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, resource_score=0.0, reason="evaluation error: " + str(error))
    report.update(runtime_seconds=time.perf_counter() - started, target_id=SPEC["target_id"], submitted_code_executed=False)
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate only the static root witness.json against the frozen finite assay.")
    parser.add_argument("witness", nargs="?", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--submission-dir", type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    if sum(value is not None for value in (arguments.witness, arguments.artifact, arguments.submission_dir)) > 1:
        parser.error("choose one artifact path or submission directory")
    witness = arguments.witness or arguments.artifact or ((arguments.submission_dir or Path.cwd()) / "witness.json")
    serialized = json.dumps(evaluate(witness), indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()

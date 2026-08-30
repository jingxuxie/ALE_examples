import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = Path(__file__).resolve().parent / "hidden"
TARGET = json.loads((HIDDEN / "target.json").read_text())


def evaluate(witness):
    started = time.perf_counter()
    environment = os.environ.copy()
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        environment[variable] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    try:
        process = subprocess.run(
            [sys.executable, "-I", str(HIDDEN / "verify.py"), os.path.abspath(witness)],
            cwd=HIDDEN,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            timeout=TARGET["evaluator_wall_seconds"],
            check=False,
        )
        if process.returncode != 0:
            report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=None, reason="validator failed or exceeded resource limit", resource_score=0.0)
        else:
            report = json.loads(process.stdout)
            report["resource_score"] = 0.0 if report["reason"].startswith("invalid witness:") else 1.0
    except subprocess.TimeoutExpired:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=None, reason="validator wall-time limit exceeded", resource_score=0.0)
    except (ValueError, OSError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=None, reason="evaluation error: " + str(error), resource_score=0.0)
    report.update(runtime_seconds=time.perf_counter() - started, target_id=TARGET["target_id"], submitted_code_executed=False)
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate one static witness.json; never run participant code.")
    parser.add_argument("witness", nargs="?", type=Path)
    parser.add_argument("--submission-dir", type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    if arguments.witness is not None and arguments.submission_dir is not None:
        parser.error("choose a witness path or --submission-dir, not both")
    witness = arguments.witness or ((arguments.submission_dir or ROOT / "participant" / "output") / "witness.json")
    report = evaluate(witness)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report is not None:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()

"""Run only the remaining build checks after the private source pool exits."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(relative, *arguments, serialized=False, expected_returncode=0):
    script = ROOT / relative
    command = [sys.executable, "-B"]
    if serialized:
        command.append(str(ROOT / "evaluator/serial.py"))
    command.extend([str(script), *map(str, arguments)])
    print("CHECK", relative, *arguments, flush=True)
    result = subprocess.run(command, cwd=ROOT, timeout=1800)
    if result.returncode != expected_returncode:
        raise RuntimeError(f"{relative}: exit {result.returncode}, expected {expected_returncode}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-pid", type=int, required=True)
    arguments = parser.parse_args()
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"
    while Path(f"/proc/{arguments.generation_pid}/cmdline").exists():
        time.sleep(5)
    generation = json.loads((ROOT / "evaluator/hidden/generation_report.json").read_text())
    assert set(generation["splits"]) == {"train", "validation", "test"}, generation
    run("evaluator/hidden/verify_generation.py")
    run("participant/baseline/train.py", "--output-dir", ROOT / "participant/baseline")
    run("evaluator/check_public_workflow.py")
    run("evaluator/run_checks.py", serialized=True)
    run("evaluator/check_assets.py", serialized=True)
    for split in ("validation", "test"):
        run("evaluator/evaluate.py", ROOT / "participant/baseline", "--split", split,
            "--report", ROOT / "attempts" / f"kernel_{split}.json", serialized=True)
    run("evaluator/evaluate.py", ROOT / "participant/baseline_exact",
        "--report", ROOT / "attempts/exact_hidden_budget.json", serialized=True, expected_returncode=2)
    report = json.loads((ROOT / "attempts/exact_hidden_budget.json").read_text())
    assert report["reason"] in {"wall_time_limit_exceeded", "sandbox_or_solver_exit_137",
                                "sandbox_or_solver_exit_152"}, report
    assert not report["valid"] and not report["passed"], report
    (ROOT / "evaluator/hidden/remaining_checks.json").write_text(json.dumps({"passed": True,
        "generation_complete": True, "fresh_agent_launched": False}, indent=2) + "\n")
    print("ALL REMAINING CHECKS PASSED; READY FOR BUILDER FREEZE", flush=True)


if __name__ == "__main__":
    main()

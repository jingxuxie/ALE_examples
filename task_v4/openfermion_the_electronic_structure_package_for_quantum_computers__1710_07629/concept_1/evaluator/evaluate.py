import argparse
import importlib.util
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from sandbox import sandbox_command


ROOT = Path(__file__).resolve().parents[1]
CORE_TARGET = 0.25
FAMILY_TARGET = 0.10
TIME_LIMIT = 180
MAX_BYTES = 8 * 1024 * 1024


def validate_solution(case, solution):
    orbital = np.asarray(solution["orbital"], dtype=float)
    auxiliary = np.asarray(solution["auxiliary"], dtype=float)
    one_body = np.asarray(case["one_body"], dtype=float)
    factors = np.asarray(case["factors"], dtype=float)
    if orbital.shape != one_body.shape or auxiliary.shape != (len(factors), len(factors)):
        raise ValueError("wrong matrix dimensions")
    for matrix in (orbital, auxiliary):
        if not np.isfinite(matrix).all():
            raise ValueError("nonfinite matrix")
        if np.linalg.norm(matrix.T @ matrix - np.eye(len(matrix))) > 1e-7:
            raise ValueError("nonorthogonal matrix")
    rotated = np.stack([orbital.T @ factor @ orbital for factor in factors])
    mixed = np.tensordot(auxiliary, rotated, axes=(1, 0))
    weights = np.abs(mixed).sum(axis=(1, 2))
    value = float(np.abs(orbital.T @ one_body @ orbital).sum() + 0.5 * np.sum(weights ** 2))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("nonpositive/nonfinite objective")
    return value


def score(request, response, elapsed, artifact=False):
    entries = response["solutions"]
    if not isinstance(entries, list) or len(entries) != len(request["cases"]):
        raise ValueError("incorrect number of solutions")
    solutions = {entry["id"]: entry for entry in entries}
    if len(solutions) != len(entries) or set(solutions) != {case["id"] for case in request["cases"]}:
        raise ValueError("missing, duplicate or unknown case ids")
    ratios = []
    family_ratios = defaultdict(list)
    details = []
    for case in request["cases"]:
        value = validate_solution(case, solutions[case["id"]])
        ratio = value / case["baseline_cost"]
        ratios.append(ratio)
        family_ratios[case["family"]].append(ratio)
        details.append({"id": case["id"], "family": case["family"], "cost": value, "baseline_cost": case["baseline_cost"], "reduction": 1 - ratio})
    reduction = lambda values: 1 - math.exp(float(np.log(values).mean()))
    core = reduction(ratios)
    families = {family: reduction(values) for family, values in family_ratios.items()}
    worst = min(families.values())
    passed = core >= CORE_TARGET and worst >= FAMILY_TARGET and elapsed <= TIME_LIMIT
    return {"core_score": core, "worst_family_score": worst, "family_scores": families, "runtime_seconds": elapsed, "resource_score": max(0, 1 - elapsed / TIME_LIMIT), "valid": True, "passed": passed, "reason": "fixed quality and resource targets met" if passed else "aggregate or worst-family target not met", "targets": {"core_score": CORE_TARGET, "worst_family_score": FAMILY_TARGET, "runtime_seconds": TIME_LIMIT}, "artifact_only": artifact, "cases": details}


def evaluate(submission, cases_path=None, artifact=False):
    request = json.loads((cases_path or ROOT / "evaluator/hidden/cases.json").read_text())
    submission = submission.resolve(strict=True)
    if artifact:
        response = json.loads((submission / "solution.json").read_text())
        return score(request, response, 0, artifact=True)
    solver = submission / "solver.py"
    if not solver.is_file():
        raise ValueError("submission must contain solver.py")
    with tempfile.TemporaryDirectory(prefix="of-gauge-eval-") as temporary:
        scratch = Path(temporary)
        request_path = scratch / "request.json"
        response_path = scratch / "response.json"
        request_path.write_text(json.dumps(request, allow_nan=False))
        command = ["/usr/bin/python3", str(solver), str(request_path), str(response_path)]
        argv, environment = sandbox_command(command, {}, ROOT / "participant", submission, scratch, cpu_seconds=TIME_LIMIT, memory_mb=2048)
        started = time.monotonic()
        with (scratch / "stdout").open("wb") as stdout, (scratch / "stderr").open("wb") as stderr:
            process = subprocess.Popen(argv, env=environment, cwd=submission, start_new_session=True, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started > TIME_LIMIT:
                        raise TimeoutError("inference exceeded 180-second wall limit")
                    if any(path.exists() and path.stat().st_size > MAX_BYTES for path in (response_path, scratch / "stdout", scratch / "stderr")):
                        raise ValueError("output exceeds size limit")
                    time.sleep(0.02)
            except BaseException:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
        elapsed = time.monotonic() - started
        if process.returncode != 0:
            error = (scratch / "stderr").read_text(errors="replace")[-2500:]
            raise RuntimeError(f"solver exited {process.returncode}: {error}")
        if not response_path.is_file() or response_path.stat().st_size > MAX_BYTES:
            raise ValueError("response missing or oversized")
        response = json.loads(response_path.read_text())
        return score(request, response, elapsed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--artifact", action="store_true")
    arguments = parser.parse_args()
    try:
        report = evaluate(arguments.submission, arguments.cases, arguments.artifact)
    except Exception as error:
        report = {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0, "passed": False, "valid": False, "reason": str(error)}
    serialized = json.dumps(report, indent=2, allow_nan=False)
    if arguments.report:
        arguments.report.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()

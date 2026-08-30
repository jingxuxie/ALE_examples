import argparse
import json
import math
import os
import resource
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FAMILIES = ["generic", "soft", "collinear", "double_collinear", "triple_collinear"]


def score(prediction, labels, families):
    if prediction.shape != labels.shape or not np.isfinite(prediction).all():
        raise ValueError("predictions must be finite and have shape (N,)")
    difference = prediction - labels
    with np.errstate(over="ignore", invalid="ignore"):
        rmse = float(np.sqrt(np.mean(difference ** 2)))
    if not math.isfinite(rmse):
        raise ValueError("prediction error is outside the finite scoring range")
    per_family = {name: float(np.sqrt(np.mean(difference[families == index] ** 2)))
                  for index, name in enumerate(FAMILIES)}
    worst = max(per_family.values())
    accurate = float(np.mean(np.abs(np.expm1(np.clip(difference, -700, 700))) <= 0.15))
    passed = rmse <= 0.05 and worst <= 0.08 and accurate >= 0.95
    return {"core_score": math.exp(-rmse), "worst_family_score": math.exp(-worst),
            "log_rmse": rmse, "worst_family_log_rmse": worst,
            "family_log_rmse": per_family, "within_15_percent": accurate,
            "passed": passed, "valid": True,
            "reason": "all prediction targets met" if passed else "prediction accuracy target not met"}


def limit_resources():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2, 128 * 1024 ** 2))
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def isolated_command(submission, query):
    command = ["bwrap", "--die-with-parent", "--unshare-all", "--new-session"]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    for path in ("/etc/alternatives", "/etc/ld.so.cache"):
        if Path(path).exists():
            command.extend(["--ro-bind", path, path])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(submission), "/submission",
                    "--ro-bind", str(HERE / "trusted_runner.py"), "/trusted/runner.py",
                    "--bind", str(query), "/query", "--chdir", "/submission",
                    "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                    "--setenv", "HOME", "/tmp", "--setenv", "OPENBLAS_NUM_THREADS", "1",
                    "--setenv", "OMP_NUM_THREADS", "1", "--setenv", "MKL_NUM_THREADS", "1",
                    "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                    "/usr/bin/python3", "/trusted/runner.py"])
    return command


def evaluate(submission):
    started = time.monotonic()
    submission = Path(submission).resolve()
    if not (submission / "predict.py").is_file():
        raise ValueError("submission must contain predict.py")
    size = sum(path.stat().st_size for path in submission.rglob("*") if path.is_file())
    if size > 128 * 1024 ** 2:
        raise ValueError("submission exceeds 128 MiB")
    data = np.load(HERE / "hidden/test.npz", allow_pickle=False)
    with tempfile.TemporaryDirectory(prefix="eerad3-prediction-") as temporary:
        query = Path(temporary)
        np.savez(query / "input.npz", s=data["s"], p=data["p"], family=data["family"])
        completed = subprocess.run(isolated_command(submission, query), capture_output=True,
                                   timeout=95, preexec_fn=limit_resources)
        if completed.returncode:
            raise ValueError("predictor failed: " + (completed.stdout + completed.stderr).decode(errors="replace")[-4000:])
        accounting = json.loads(completed.stdout)
        cpu_seconds = float(accounting["cpu_seconds"])
        if accounting["returncode"] != 0 or not math.isfinite(cpu_seconds) or cpu_seconds <= 0:
            raise ValueError("invalid trusted CPU accounting record")
        if not (query / "output.npz").is_file():
            raise ValueError("predictor did not create output.npz")
        with np.load(query / "output.npz", allow_pickle=False) as output:
            prediction = np.asarray(output["log_weight"], dtype=np.float64)
        result = score(prediction, data["log_weight"], data["family"])
    elapsed = time.monotonic() - started
    result.update(wall_seconds=elapsed, runtime_score=max(0.0, 1.0 - elapsed / 90), artifact_bytes=size)
    resource_path = HERE / "hidden/resource.json"
    if resource_path.exists():
        contract = json.loads(resource_path.read_text())
        budget = contract["cpu_seconds_per_million"] * len(prediction) / 1e6
        result.update(cpu_seconds=cpu_seconds, cpu_budget_seconds=budget,
                      cpu_seconds_per_million=cpu_seconds / len(prediction) * 1e6,
                      runtime_score=min(1.0, budget / max(cpu_seconds, 1e-12)))
        if cpu_seconds > budget:
            result.update(passed=False, reason="production CPU throughput target not met")
    if elapsed > 90:
        result.update(passed=False, reason="runtime target not met")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--report")
    arguments = parser.parse_args()
    try:
        result = evaluate(arguments.submission)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
                  "passed": False, "valid": False, "reason": str(error)}
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    print(encoded, end="")
    if arguments.report:
        Path(arguments.report).write_text(encoded)


if __name__ == "__main__":
    main()

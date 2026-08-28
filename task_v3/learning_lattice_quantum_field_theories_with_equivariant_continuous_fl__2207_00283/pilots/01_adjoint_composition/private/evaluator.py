"""Private, reference-output evaluator for pilot 01."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FAMILIES = (
    "primal", "time_gradient", "parameter_gradient", "input_gradient",
    "density", "inverse", "acceptance",
)


def constrained_environment():
    environment = os.environ.copy()
    environment.update({
        "JAX_PLATFORM_NAME": "cpu", "JAX_ENABLE_X64": "true",
        "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4", "TF_NUM_INTRAOP_THREADS": "4",
        "TF_NUM_INTEROP_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "XLA_FLAGS": "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4",
    })
    environment.pop("PYTHONPATH", None)
    return environment


def limit_affinity():
    if hasattr(os, "sched_getaffinity"):
        available = sorted(os.sched_getaffinity(0))
        preferred = [cpu for cpu in range(32, 36) if cpu in available]
        os.sched_setaffinity(0, preferred or available[:4])


def public_mount_paths(path, requested=None):
    paths = {str(path.absolute()), str(path.resolve())}
    if requested is not None:
        paths.add(str(requested.absolute()))
    for original in tuple(paths):
        if original.startswith("/home/"):
            paths.add("/srv" + original)
        elif original.startswith("/srv/home/"):
            paths.add(original[len("/srv"):])
    return sorted(paths)


def sandbox_command(submission, temporary, requested_submission=None):
    participant = ROOT / "participant"
    runtime = participant / "input/runtime/bin/python3.12"
    if not runtime.is_file():
        raise RuntimeError("the supplied participant runtime is missing")
    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise RuntimeError("bwrap is required for participant evaluation")
    command = [bubblewrap, "--die-with-parent", "--unshare-all", "--new-session"]
    for directory in ("/usr", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    command.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(participant), "/task",
        "--ro-bind", str(submission), "/submission",
        "--bind", str(temporary), "/work", "--chdir", "/submission", "--clearenv",
    ])
    for public_root, requested in ((participant, None), (submission, requested_submission)):
        for destination in public_mount_paths(public_root, requested):
            command.extend(["--ro-bind", str(public_root), destination])
    environment = {
        "PATH": "/task/input/runtime/bin:/usr/bin:/bin", "HOME": "/tmp",
        "PYTHONPATH": "/submission:/task/workspace", "PYTHONNOUSERSITE": "1",
        "JAX_PLATFORM_NAME": "cpu", "JAX_PLATFORMS": "cpu", "JAX_ENABLE_X64": "true",
        "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
        "TF_NUM_INTRAOP_THREADS": "4", "TF_NUM_INTEROP_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "XLA_FLAGS": "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4",
    }
    for name, value in environment.items():
        command.extend(["--setenv", name, value])
    command.extend([
        "--", "/task/input/runtime/bin/python3.12", "-B", "/submission/solve.py",
        "--input", "/work/request.json", "--output", "/work/response.json",
    ])
    return command


def run_submission(submission, request, timeout=240, trusted_reference=False):
    requested_submission = Path(submission).absolute()
    submission = requested_submission.resolve()
    if not (submission / "solve.py").is_file() and (submission / "workspace/solve.py").is_file():
        submission = submission / "workspace"
        requested_submission = requested_submission / "workspace"
    if not (submission / "solve.py").is_file():
        raise ValueError("submission directory must contain solve.py")
    trusted_directories = {
        (ROOT / "private/reference/implementation").resolve(),
        (ROOT / "private/baselines/weak").resolve(),
    }
    if trusted_reference and submission not in trusted_directories:
        raise ValueError("trusted execution is restricted to the preserved private reference/baseline")
    if not trusted_reference and submission.is_relative_to(ROOT / "private"):
        raise ValueError("private implementations require explicit --trusted-reference")
    runtime = ROOT / "participant/input/runtime/bin/python3.12"
    executable = str(runtime) if runtime.is_file() else os.environ.get("ALE_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="adjoint-evaluation-") as temporary:
        input_path = Path(temporary) / "request.json"
        output_path = Path(temporary) / "response.json"
        input_path.write_text(json.dumps(request))
        command = (
            [executable, str(submission / "solve.py"), "--input", str(input_path),
             "--output", str(output_path)]
            if trusted_reference else sandbox_command(submission, temporary, requested_submission)
        )
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=submission, env=constrained_environment(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, preexec_fn=limit_affinity, start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise TimeoutError(f"submission exceeded {timeout} seconds") from None
        elapsed = time.monotonic() - started
        if process.returncode != 0:
            raise RuntimeError(f"submission exited {process.returncode}: {stderr[-4000:]}")
        return json.loads(output_path.read_text()), elapsed, stderr[-2000:]


def field_error(prediction, expected):
    try:
        prediction = np.asarray(prediction, dtype=float)
        expected = np.asarray(expected, dtype=float)
        if prediction.shape != expected.shape or not np.all(np.isfinite(prediction)):
            return math.inf
        return float(np.sqrt(np.mean((prediction - expected) ** 2)) /
                     (1.0 + np.sqrt(np.mean(expected**2))))
    except (ValueError, TypeError):
        return math.inf


def measure(request, prediction, reference):
    errors = {family: [] for family in FAMILIES}
    failures = []
    results = prediction.get("results", {})
    expected_results = reference["results"]
    for case in request["cases"]:
        result = results.get(case["id"], {})
        expected = expected_results[case["id"]]
        if not isinstance(result, dict):
            result = {}
        if "error" in result or not result:
            failures.append({"id": case["id"], "error": result.get("error", "missing result")})
        if case["kind"] == "flow":
            mapping = {
                "state": "primal" if case["direction"] == "forward" else "inverse",
                "log_density": "density", "time_gradient": "time_gradient",
                "parameter_gradient": "parameter_gradient", "input_gradient": "input_gradient",
            }
        else:
            mapping = {
                "proposal_states": "primal", "proposal_log_density": "density",
                "log_acceptance": "acceptance", "retained_states": "acceptance",
                "accepted": "acceptance",
            }
        for field, family in mapping.items():
            errors[family].append(field_error(result.get(field), expected[field]))
    aggregate = {
        family: float(np.sqrt(np.mean(np.square(values)))) if values else math.inf
        for family, values in errors.items()
    }
    return aggregate, failures


def score_errors(errors, calibration):
    scores = {
        family: 1.0 / (1.0 + error / calibration[family]["scale"])
        if math.isfinite(error) else 0.0
        for family, error in errors.items()
    }
    return float(np.mean(list(scores.values()))), scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--pool", choices=("standard", "challenge"), default="standard")
    parser.add_argument("--trusted-reference", action="store_true",
                        help="bypass isolation only for preserved private reference/baseline code")
    arguments = parser.parse_args()
    pool = ROOT / "private/challenge_pool" / arguments.pool
    request = json.loads((pool / "request.json").read_text())
    reference = json.loads((pool / "reference.json").read_text())
    calibration = json.loads((pool / "calibration.json").read_text())
    try:
        prediction, elapsed, stderr = run_submission(
            arguments.submission, request, trusted_reference=arguments.trusted_reference
        )
        errors, failures = measure(request, prediction, reference)
        score, families = score_errors(errors, calibration)
        report = {"score": score, "family_scores": families,
                  "family_errors": {key: value if math.isfinite(value) else None
                                    for key, value in errors.items()},
                  "failures": failures, "elapsed_seconds": elapsed, "stderr": stderr}
    except Exception as error:
        report = {"score": 0.0, "family_scores": dict.fromkeys(FAMILIES, 0.0),
                  "error": f"{type(error).__name__}: {error}"}
    report["pool"] = arguments.pool
    report["execution_mode"] = "trusted_reference" if arguments.trusted_reference else "bwrap"
    report_path = Path(arguments.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"score": report["score"], "pool": arguments.pool}))


if __name__ == "__main__":
    main()

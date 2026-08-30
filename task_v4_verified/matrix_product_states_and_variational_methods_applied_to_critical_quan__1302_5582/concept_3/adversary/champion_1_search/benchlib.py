import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

import numpy as np


SIDECAR = Path(__file__).resolve().parent
CONCEPT = SIDECAR.parents[1]
sys.path.insert(0, str(CONCEPT / "evaluator"))
import evaluate


def read(path):
    return evaluate.load_json(Path(path))


def write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare():
    original_root = evaluate.ROOT
    evaluate.ROOT = CONCEPT
    evaluate.verify_integrity()
    evaluate.ROOT = original_root
    runner = SIDECAR / "evaluator/runner.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONCEPT / "evaluator/runner.py", runner)
    submission = SIDECAR / "submission_original"
    submission.mkdir(exist_ok=True)
    shutil.copyfile(CONCEPT / "attempts/v_1/predict.py", submission / "predict.py")
    return submission, read(CONCEPT / "evaluator/hidden/target_contract.json")["resources"]


def run_isolated(submission, inputs, limits, empty_training=False):
    directory = SIDECAR / "runs"
    directory.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="batch-", dir=directory) as temporary:
        stage = Path(temporary)
        evaluate.stage_submission(submission, stage / "submission", limits["submission_mib"] * 1024 ** 2)
        if empty_training:
            (stage / "public").mkdir()
            write(stage / "public/train.json", {"schema_version": 1, "cases": []})
        else:
            shutil.copytree(CONCEPT / "participant/input", stage / "public")
        write(stage / "input.json", inputs)
        write(stage / "limits.json", limits)
        (stage / "output").mkdir()
        original_root = evaluate.ROOT
        evaluate.ROOT = SIDECAR
        try:
            command = evaluate.sandbox_command(stage)
        finally:
            evaluate.ROOT = original_root
        entrypoint = '    runpy.run_path(sys.argv[0], run_name="__main__")'
        profiling = '''    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        Path("/output/resource_usage.json").write_text(json.dumps({
            "cpu_seconds": usage.ru_utime + usage.ru_stime,
            "max_rss_mib": usage.ru_maxrss / 1024.0
        }, allow_nan=False))'''
        if command[-1].count(entrypoint) != 1:
            raise RuntimeError("Trusted bootstrap changed; refusing uninstrumented profiling")
        command[-1] = command[-1].replace(entrypoint, profiling)
        compile(command[-1], "<trusted-profile-bootstrap>", "exec")
        started = time.monotonic()
        timeout = False
        with (stage / "stderr.log").open("wb") as error_stream:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=error_stream, start_new_session=True, close_fds=True, env={"PATH": "/usr/bin:/bin"})
            while True:
                waited, status, usage = os.wait4(process.pid, os.WNOHANG)
                if waited:
                    break
                if time.monotonic() - started > limits["wall_seconds"]:
                    timeout = True
                    os.killpg(process.pid, signal.SIGKILL)
                    waited, status, usage = os.wait4(process.pid, 0)
                    break
                time.sleep(0.02)
            process.returncode = os.waitstatus_to_exitcode(status)
        timing = {"wall_seconds": time.monotonic() - started,
                  "launcher_cpu_seconds": usage.ru_utime + usage.ru_stime,
                  "launcher_max_rss_mib": usage.ru_maxrss / 1024.0,
                  "returncode": process.returncode, "wall_timeout": timeout,
                  "resource_source": "trusted-bootstrap self getrusage; launcher wait4 recorded separately",
                  "solver_profile_available": False, "cpu_seconds": None, "max_rss_mib": None}
        profile_path = stage / "output/resource_usage.json"
        if profile_path.exists():
            profile = read(profile_path)
            timing.update(profile)
            timing["solver_profile_available"] = True
        if process.returncode or timeout:
            timing["status"] = "resource_or_execution_failure"
            timing["stderr_tail"] = (stage / "stderr.log").read_bytes()[-1200:].decode(errors="replace")
            return None, timing
        payload = read(stage / "output/predictions.json")
        evaluate.parse_predictions(payload, [case["id"] for case in inputs["cases"]])
        diagnostic_path = stage / "output/diagnostics.json"
        if diagnostic_path.exists():
            timing["solver_diagnostics"] = read(diagnostic_path)
        timing["status"] = "ok"
        return payload, timing


def score(payload, inputs, labels):
    identifiers = [case["id"] for case in inputs["cases"]]
    predicted = evaluate.parse_predictions(payload, identifiers)
    reference = evaluate.parse_predictions(labels, identifiers)
    families = [case["family"] for case in inputs["cases"]]
    metrics = evaluate.score_predictions(predicted, reference, families)
    signed = np.log(predicted) - np.log(reference)
    errors = np.abs(signed)
    worst = []
    for flattened in np.argsort(errors.ravel())[-12:][::-1]:
        row, column = np.unravel_index(flattened, errors.shape)
        case = inputs["cases"][row]
        scale = (case["lambda"] / 6.0) ** (1.0 / 3.0)
        worst.append({"id": identifiers[row], "family": families[row], "target": evaluate.TARGETS[column],
                      "absolute_log_error": float(errors[row, column]),
                      "relative_error": float(abs(np.expm1(signed[row, column]))),
                      "predicted": float(predicted[row, column]), "reference": float(reference[row, column]),
                      "r": case["mu2"] / scale ** 2, "j": case["kappa"] / scale ** 2})
    metrics["worst_cells"] = worst
    metrics["max_log_error"] = float(errors.max())
    metrics["cells_above_0_12_log_error"] = int(np.count_nonzero(errors > 0.12))
    return metrics


def participant_unchanged():
    initial = read(SIDECAR / "private/original_participant_hashes.json")
    current = {str(path.relative_to(CONCEPT)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in (CONCEPT / "participant").rglob("*") if path.is_file()}
    return initial == current

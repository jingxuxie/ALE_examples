import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "private"))
from evaluation_sandbox import restrict_solver

sys.path.insert(0, str(ROOT / "private" / "reference"))
from metrics import grade, load_output, measure


def confine(submission, work):
    restrict_solver(submission.parent, work, seconds=120, gibibytes=2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def run_solver(submission, input_path, output_copy=None):
    start = time.monotonic()
    attempt = ROOT / "attempt"
    attempt.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eval_", dir=attempt) as temporary:
        work = Path(temporary).resolve()
        staged_submission = work / "solver.py"
        shutil.copyfile(submission, staged_submission)
        shutil.copyfile(input_path, work / "input.npz")
        environment = dict(PATH="/usr/bin:/bin", HOME=str(work), TMPDIR=str(work), NUMBA_CACHE_DIR=str(work / "cache"), OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="0", LANG="C.UTF-8")
        with (work / "process.log").open("w+b") as log:
            try:
                process = subprocess.Popen([sys.executable, "-I", "-B", str(staged_submission), str(work / "input.npz"), str(work / "output.npz")], cwd=work, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=lambda: confine(staged_submission, work))
            except Exception as error:
                return None, dict(status="sandbox_error", error=str(error), runtime_seconds=time.monotonic() - start)
            try:
                returncode = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return None, dict(status="timeout", runtime_seconds=time.monotonic() - start)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            log.seek(0, os.SEEK_END)
            log.seek(max(0, log.tell() - 3000))
            log_tail = log.read().decode(errors="replace")
        details = dict(status="ok", runtime_seconds=time.monotonic() - start, exit_code=returncode)
        if returncode:
            details.update(status="solver_error", error=log_tail)
            return None, details
        try:
            with np.load(input_path, allow_pickle=False) as data:
                prediction = load_output(work / "output.npz", int(data["n_qubits"]), int(data["max_terms"]))
        except Exception as error:
            details.update(status="invalid_output", error=str(error))
            return None, details
        if output_copy is not None:
            output_copy = Path(output_copy)
            output_copy.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(output_copy, **prediction)
        return prediction, details


def evaluate(submission, directory):
    start = time.monotonic()
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    if not manifest.get("calibrated"):
        raise ValueError("case pool must be calibrated by reference/benchmark.py")
    cases = []
    for record in manifest["cases"]:
        input_path = directory / record["input"]
        prediction, details = run_solver(submission, input_path)
        result = dict(id=record["id"], family=record["family"], **details)
        if prediction is None:
            result.update(score=0.0, recovery_score=0.0, estimation_score=0.0)
        else:
            with np.load(directory / record["truth"], allow_pickle=False) as archive:
                truth = {key: archive[key] for key in archive.files}
            with np.load(input_path, allow_pickle=False) as data:
                metrics = measure(prediction, truth, float(data["recovery_floor"]))
            result.update(grade(metrics, record["calibration"]))
        cases.append(result)
    families = {}
    for family in sorted({case["family"] for case in cases}):
        selected = [case for case in cases if case["family"] == family]
        families[family] = {key: float(np.mean([case[key] for case in selected])) for key in ("score", "recovery_score", "estimation_score", "runtime_seconds")}
        families[family]["count"] = len(selected)
    mean = float(np.mean([case["score"] for case in cases]))
    return dict(schema_version=1, pool=manifest["pool"], region=manifest["region"], mean_core=mean if manifest["pool"] == "core" else None, mean_score=mean, worst_family=min(family["score"] for family in families.values()), families=families, cases=cases, runtime_seconds=time.monotonic() - start, limits=dict(wall_seconds=120, address_space_gib=2, threads=1), sandbox="Landlock; staged solver directory only")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--pool", choices=("core", "challenge"), default="core")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--case-root", type=Path)
    args = parser.parse_args()
    directory = args.case_root or ROOT / "private" / ("reference/core" if args.pool == "core" else "challenge_pool")
    report = evaluate(args.submission.resolve(), directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("mean_core", "mean_score", "worst_family", "runtime_seconds")}))


if __name__ == "__main__":
    main()

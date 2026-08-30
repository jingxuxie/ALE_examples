import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
PARTICIPANT = ROOT / "participant"
SANDBOX = ROOT.parent / "authoring" / "sandbox.py"


def check_frozen():
    frozen = json.loads((ROOT / "evaluator" / "frozen.json").read_text())
    for relative, expected in frozen["sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen artifact mismatch: " + relative)


def verify_submission(source):
    source = source.resolve(strict=True)
    if not source.is_dir() or not (source / "solve.py").is_file():
        raise ValueError("submission directory must contain solve.py")
    total = 0
    for directory, folders, files in os.walk(source, followlinks=False):
        for name in folders + files:
            path = Path(directory) / name
            information = path.lstat()
            if not stat.S_ISREG(information.st_mode) and not stat.S_ISDIR(information.st_mode):
                raise ValueError("submission links and special files are forbidden")
            if stat.S_ISREG(information.st_mode):
                total += information.st_size
                if information.st_nlink != 1:
                    raise ValueError("submission hard links forbidden")
    if total > 256 * 1024**2:
        raise ValueError("submission exceeds 256 MiB")
    return source


def load_prediction(path, shots):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_size > 64 * 1024**2:
            raise ValueError("invalid output file")
        content = stream.read()
    stream = io.BytesIO(content)
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(stream)
    else:
        raise ValueError("unsupported npy version")
    if shape not in [(shots,), (shots, 1)] or dtype not in [np.dtype("bool"), np.dtype("uint8")]:
        raise ValueError("output must be bool/uint8, shape (shots,) or (shots,1)")
    if len(content) - stream.tell() != shots:
        raise ValueError("incorrect npy payload size")
    prediction = np.load(io.BytesIO(content), allow_pickle=False).reshape(-1)
    if not np.isin(prediction, [0, 1]).all():
        raise ValueError("non-binary prediction")
    return prediction


def run_case(submission, case):
    with tempfile.TemporaryDirectory(prefix="honeycomb_decode_") as temporary:
        scratch = Path(temporary)
        request = scratch / "request"
        shutil.copytree(HIDDEN / "requests" / case["id"], request)
        output = scratch / "prediction.npy"
        command = [sys.executable, str(SANDBOX), "--submission", str(submission),
                   "--participant", str(PARTICIPANT), "--scratch", str(scratch),
                   "--seconds", "60", "--memory-mib", "4096", "--", str(request), str(output)]
        start = time.monotonic()
        with (scratch / "stdout").open("wb") as stdout, (scratch / "stderr").open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise ValueError("60-second request limit exceeded")
        elapsed = time.monotonic() - start
        if process.returncode != 0:
            diagnostic = (scratch / "stderr").read_text(errors="replace")[-1500:]
            raise ValueError(f"submission exit {process.returncode}: {diagnostic}")
        return load_prediction(output, case["shots"]), elapsed


def evaluate(submission):
    check_frozen()
    submission = verify_submission(submission)
    cases = json.loads((HIDDEN / "manifest.json").read_text())
    family_totals = {}
    results = []
    paired_delta = 0
    discordant = 0
    total_shots = 0
    for case in cases:
        prediction, elapsed = run_case(submission, case)
        truth = np.load(HIDDEN / "labels" / (case["id"] + ".npy"), allow_pickle=False)
        baseline = np.load(HIDDEN / "baseline" / (case["id"] + ".npy"), allow_pickle=False)
        baseline_wrong = baseline != truth
        candidate_wrong = prediction != truth
        baseline_errors = int(np.count_nonzero(baseline_wrong))
        errors = int(np.count_nonzero(candidate_wrong))
        if baseline_errors != case["baseline_errors"]:
            raise ValueError("baseline accounting mismatch")
        totals = family_totals.setdefault(case["family"], {"errors": 0, "baseline_errors": 0, "shots": 0})
        totals["errors"] += errors
        totals["baseline_errors"] += baseline_errors
        totals["shots"] += case["shots"]
        paired_delta += baseline_errors - errors
        discordant += int(np.count_nonzero(baseline_wrong != candidate_wrong))
        total_shots += case["shots"]
        results.append({"id": case["id"], "family": case["family"], "errors": errors,
                        "baseline_errors": baseline_errors, "shots": case["shots"], "seconds": elapsed})
    ratios = {family: values["errors"] / values["baseline_errors"] for family, values in family_totals.items()}
    core = sum(ratios.values()) / len(ratios)
    worst = max(ratios.values())
    variance = max(1.0, discordant - paired_delta**2 / total_shots)
    sigma = paired_delta / math.sqrt(variance)
    passed = core <= 0.8 and worst <= 0.95 and sigma >= 3
    elapsed = sum(case["seconds"] for case in results)
    return {"core_score": 1 - core, "core_failure_ratio": core,
            "worst_family_score": 1 - worst, "worst_family_ratio": worst,
            "family_ratios": ratios, "family_totals": family_totals, "paired_sigma": sigma,
            "runtime_seconds": elapsed, "resource_score": max(0, 1 - elapsed / (60 * len(cases))),
            "valid": True, "passed": passed,
            "reason": "fixed improvement target met" if passed else "fixed quality or worst-family target not met",
            "cases": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        result = evaluate(arguments.submission)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
                  "valid": False, "passed": False, "reason": str(error)}
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()

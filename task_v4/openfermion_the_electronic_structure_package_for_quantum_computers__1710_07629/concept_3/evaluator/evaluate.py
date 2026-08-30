"""Guarded CLI: python3 evaluator/evaluate.py SUBMISSION_DIR [--report JSON]."""

import argparse
import json
import os
from pathlib import Path
import resource
import secrets
import selectors
import stat
import subprocess
import sys
import tempfile
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from isolation import sandbox_command
from scoring import parse_predictions, score_predictions


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "evaluator"
INPUT_KEYS = ("hopping", "interaction", "potential", "n_sites", "family")


def overlap(first, second):
    return first == second or first in second.parents or second in first.parents


def check_submission(submission, settings):
    if not submission.is_dir() or overlap(submission, PRIVATE):
        raise ValueError("submission must be a directory disjoint from evaluator")
    if not (submission / "solver.py").is_file():
        raise ValueError("submission has no solver.py")
    total = 0
    count = 0
    for directory, subdirectories, filenames in os.walk(submission, followlinks=False):
        for name in subdirectories + filenames:
            entry = Path(directory) / name
            metadata = entry.lstat()
            count += 1
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("submission symlinks are forbidden")
            if not stat.S_ISREG(metadata.st_mode) and not stat.S_ISDIR(metadata.st_mode):
                raise ValueError("submission special files are forbidden")
            if stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise ValueError("submission hard links are forbidden")
                total += metadata.st_size
            if total > settings["submission_mb"] * 1024 ** 2 or count > 10000:
                raise ValueError("submission exceeds file-count or size limit")


def scratch_bytes(scratch):
    total = 0
    count = 0
    for directory, subdirectories, filenames in os.walk(scratch, followlinks=False):
        count += len(subdirectories) + len(filenames)
        if count > 1024:
            raise ValueError("scratch file-count limit exceeded")
        for name in filenames:
            metadata = (Path(directory) / name).lstat()
            if stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
    return total


def run_guarded(command, environment, submission, scratch, settings):
    argv, child_environment = sandbox_command(
        command, environment, ROOT / "participant", submission, scratch,
        cpu_seconds=settings["cpu_seconds"], memory_mb=settings["memory_mb"])
    previous = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    process = subprocess.Popen(argv, env=child_environment, cwd=submission,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
    captured = bytearray()
    total_output = 0
    failure = None
    forced_supervisor_kill = False
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    selector.register(process.stderr, selectors.EVENT_READ)
    next_disk_check = started
    try:
        while selector.get_map() or process.poll() is None:
            elapsed = time.perf_counter() - started
            if elapsed > settings["wall_seconds"]:
                failure = "wall_time_limit_exceeded"
                break
            if time.perf_counter() >= next_disk_check:
                if scratch_bytes(scratch) > settings["scratch_mb"] * 1024 ** 2:
                    failure = "scratch_size_limit_exceeded"
                    break
                next_disk_check = time.perf_counter() + 0.05
            for key, _ in selector.select(timeout=0.02):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total_output += len(chunk)
                if len(captured) < 4096:
                    captured.extend(chunk[:4096 - len(captured)])
                if total_output > settings["stdout_stderr_bytes"]:
                    failure = "stdout_stderr_limit_exceeded"
                    break
            if failure:
                break
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                forced_supervisor_kill = True
                process.kill()
        process.wait(timeout=5)
        selector.close()
        process.stdout.close()
        process.stderr.close()
    elapsed = time.perf_counter() - started
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = usage.ru_utime + usage.ru_stime - previous.ru_utime - previous.ru_stime
    if failure is None and elapsed > settings["wall_seconds"]:
        failure = "wall_time_limit_exceeded"
    if failure is None and process.returncode != 0:
        failure = "sandbox_or_solver_exit_" + str(process.returncode)
    return {"wall_seconds": elapsed,
            "cpu_seconds": None if forced_supervisor_kill else cpu,
            "cpu_measurement": "unavailable_after_hard_supervisor_kill" if forced_supervisor_kill else "waited_process_tree",
            "returncode": process.returncode, "failure": failure,
            "diagnostic": captured.decode("utf-8", errors="replace")}


def read_output(path, byte_limit):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("prediction output must be a regular unlinked file")
        if metadata.st_size > byte_limit:
            raise ValueError("prediction output byte limit exceeded")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(byte_limit + 1)
        if len(content) > byte_limit:
            raise ValueError("prediction output byte limit exceeded")
        return content.decode("utf-8")
    finally:
        os.close(descriptor)


def evaluate(submission, split="test"):
    settings = json.loads((PRIVATE / "settings.json").read_text())
    report = {"schema_version": 1, "split": split, "core_score": 0.0,
              "worst_family_score": 0.0, "resource_score": 0.0,
              "runtime_seconds": 0.0, "passed": False, "valid": False, "reason": "not_run"}
    try:
        submission = Path(submission).resolve(strict=True)
        check_submission(submission, settings)
        dataset = PRIVATE / "hidden/test.npz" if split == "test" else ROOT / "participant/input/validation.npz"
        with np.load(dataset, allow_pickle=False) as archive:
            inputs = {key: archive[key].copy() for key in INPUT_KEYS}
            labels = archive["gaps"].copy()
        count = len(labels)
        expected_count = settings["hidden_count"] if split == "test" else settings["validation_count"]
        if labels.shape != (expected_count, 2) or not np.all(np.isfinite(labels)):
            raise ValueError("invalid trusted dataset")
        permutation = np.random.default_rng(secrets.randbits(128)).permutation(count)
        runtime_root = PRIVATE / "runs"
        runtime_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="run-", dir=runtime_root) as temporary:
            scratch = Path(temporary).resolve()
            input_path = scratch / "inputs.npz"
            request_path = scratch / "request.json"
            output_path = scratch / "predictions.json"
            np.savez_compressed(input_path, **{key: value[permutation] for key, value in inputs.items()})
            request_path.write_text(json.dumps({"schema_version": 1, "inputs": str(input_path),
                "n_instances": count, "target_order": ["charge_gap", "spin_gap"]}) + "\n")
            runtime = run_guarded(["/usr/bin/python3", "-B", str(submission / "solver.py"),
                                   str(request_path), str(output_path)],
                                  {"HUBBARD_ASSET_DIR": str(ROOT / "participant/input")},
                                  submission, scratch, settings)
            report["runtime"] = runtime
            report["runtime_seconds"] = runtime["wall_seconds"]
            if runtime["failure"]:
                report["reason"] = runtime["failure"]
                return report
            predictions = parse_predictions(read_output(output_path, settings["prediction_bytes"]), count)
            report.update(score_predictions(predictions, labels[permutation],
                                            inputs["family"][permutation], settings))
            report["resource_score"] = max(0.0, 1.0 - runtime["wall_seconds"] / settings["wall_seconds"])
            report["valid"] = True
            report["passed"] = report["accuracy_passed"]
            report["reason"] = "passed" if report["passed"] else "accuracy_target_not_met"
    except Exception as error:
        report["reason"] = type(error).__name__ + ": " + str(error)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission_dir")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--split", choices=("test", "validation"), default="test")
    arguments = parser.parse_args()
    report = evaluate(arguments.submission_dir, arguments.split)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(text)
    print(text, end="")
    raise SystemExit(0 if report["valid"] else 2)


if __name__ == "__main__":
    main()

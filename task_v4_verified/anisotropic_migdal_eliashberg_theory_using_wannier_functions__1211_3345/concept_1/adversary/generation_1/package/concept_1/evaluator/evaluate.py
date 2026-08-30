"""Private scoring parent. Candidate code only executes in the shared sandbox child."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "hidden"))
from physics import INPUT_KEYS, metrics


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
POLICY_PATH = HIDDEN / "policy.json"
POLICY = json.loads(POLICY_PATH.read_text())
RUNNER = ROOT.parent / "authoring" / "sandbox_runner.py"


def safe_copy(source, destination, byte_limit=32 * 1024 ** 2):
    source = Path(os.path.abspath(source))
    if source.is_symlink() or source.resolve() != source:
        raise ValueError("symlinked submission path forbidden")
    if not source.is_dir():
        raise ValueError("submission must be a directory")
    total = 0
    destination.mkdir()
    entries = 0

    def copy_directory(directory_fd, target_directory, depth):
        nonlocal total, entries
        for name in sorted(os.listdir(directory_fd)):
            if name in ("__pycache__", ".git"):
                continue
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            entries += 1
            if entries > 512 or depth > 8:
                raise ValueError("submission tree too large")
            target = target_directory / name
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("submission symlinks forbidden")
            if stat.S_ISDIR(metadata.st_mode):
                target.mkdir(exist_ok=True)
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
                try:
                    copy_directory(child_fd, target, depth + 1)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
                if total > byte_limit:
                    raise ValueError("submission exceeds byte limit")
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
                with os.fdopen(descriptor, "rb") as handle:
                    actual = os.fstat(handle.fileno())
                    if not stat.S_ISREG(actual.st_mode) or actual.st_size != metadata.st_size:
                        raise ValueError("submission changed during copy")
                    contents = handle.read(byte_limit + 1)
                if len(contents) != metadata.st_size:
                    raise ValueError("submission changed during copy")
                target.write_bytes(contents)
            else:
                raise ValueError("nonregular submission file")
    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        copy_directory(source_fd, destination, 1)
    finally:
        os.close(source_fd)


def read_output(path, expected_shape):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        information = os.fstat(handle.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1:
            raise ValueError("output must be a regular unlinked file")
        if information.st_size > POLICY["output_bytes_max"]:
            raise ValueError("output too large")
        with zipfile.ZipFile(handle) as archive:
            entries = archive.infolist()
            if sorted(item.filename for item in entries) != ["delta.npy", "z.npy"]:
                raise ValueError("exactly delta and z are required")
            if sum(item.file_size for item in entries) > POLICY["output_bytes_max"]:
                raise ValueError("expanded output too large")
            values = {}
            for entry in entries:
                with archive.open(entry) as member:
                    version = np.lib.format.read_magic(member)
                    if version == (1, 0):
                        shape, fortran, dtype = np.lib.format.read_array_header_1_0(member)
                    elif version == (2, 0):
                        shape, fortran, dtype = np.lib.format.read_array_header_2_0(member)
                    else:
                        raise ValueError("unsupported numpy format")
                    if shape != expected_shape or dtype not in (np.dtype("float64"), np.dtype("float32")):
                        raise ValueError("invalid shape or dtype")
                with archive.open(entry) as member:
                    value = np.lib.format.read_array(member, allow_pickle=False)
                if not np.isfinite(value).all():
                    raise ValueError("nonfinite output")
                values[entry.filename[:-4]] = value.astype(np.float64)
    return values


def run_candidate(submission, instance, cpu_seconds=None, wall_seconds=None):
    cpu_limit = POLICY["cpu_seconds"] if cpu_seconds is None else cpu_seconds
    wall_limit = POLICY["wall_seconds"] if wall_seconds is None else wall_seconds
    if not RUNNER.is_file():
        raise RuntimeError("shared hardened sandbox runner is required; no insecure fallback")
    with tempfile.TemporaryDirectory(prefix="eliashberg_run_") as temporary:
        directory = Path(temporary)
        code = directory / "submission"
        public = directory / "participant"
        scratch = directory / "scratch"
        safe_copy(submission, code)
        public.mkdir()
        (public / "input").mkdir()
        (public / "workspace").mkdir()
        for public_asset in (ROOT / "participant" / "input").iterdir():
            if public_asset.is_file() and public_asset.suffix in (".py", ".md", ".json"):
                shutil.copyfile(public_asset, public / "input" / public_asset.name)
        scratch.mkdir()
        np.savez(scratch / "instance.npz", **{key: instance[key] for key in INPUT_KEYS})
        output = scratch / "solution.npz"
        command = [sys.executable, "-I", "-B", str(ROOT / "evaluator" / "launch.py"),
                   "--shared-runner", str(RUNNER), "--submission", str(code),
                   "--participant", str(public), "--input", str(scratch / "instance.npz"),
                   "--output", str(output), "--scratch", str(scratch), "--cpu-seconds", str(cpu_limit),
                   "--memory-mb", str(POLICY["memory_mb"])]
        environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(scratch),
                       "TMPDIR": str(scratch), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                       "MKL_NUM_THREADS": "1", "BLIS_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        with open(directory / "stdout.log", "wb") as standard_output, open(directory / "stderr.log", "wb") as standard_error:
            process = subprocess.Popen(command, cwd=scratch, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=standard_output, stderr=standard_error,
                                       close_fds=True, start_new_session=True)
            timed_out = False
            try:
                process.wait(timeout=wall_limit)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_used = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        execution = {"cpu_seconds": cpu_used, "wall_seconds": time.monotonic() - started,
                     "returncode": process.returncode, "wall_timeout": timed_out}
        if timed_out or process.returncode != 0 or cpu_used > cpu_limit:
            execution["error"] = "resource limit or nonzero exit"
            with open(directory / "stderr.log", "rb") as failure_log:
                execution["untrusted_stderr_prefix"] = failure_log.read(2048).decode("utf-8", errors="replace")
            return None, execution
        try:
            if output.is_symlink() or not output.resolve().is_relative_to(scratch.resolve()):
                raise ValueError("output escapes scratch or is a symlink")
            result = read_output(output, (len(instance["weights"]), int(instance["n_freq"])))
        except (OSError, ValueError, EOFError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
            execution["error"] = type(error).__name__ + ": " + str(error)
            return None, execution
        return result, execution


def accepted(measurements):
    return bool(measurements["gap_residual"] <= POLICY["gap_residual_max"]
                and measurements["z_residual"] <= POLICY["z_residual_max"]
                and measurements["branch_error"] <= POLICY["branch_error_max"]
                and measurements["sign_correct"])


def evaluate(submission, case_ids=None):
    evaluation_started = time.monotonic()
    parent_started = time.process_time()
    manifest = json.loads((HIDDEN / "manifest.json").read_text())
    reports = []
    for record in manifest["cases"]:
        case_id = record["case_id"]
        if case_ids is not None and case_id not in case_ids:
            continue
        with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as archive:
            instance = {key: archive[key] for key in INPUT_KEYS}
        with np.load(HIDDEN / "references" / (case_id + ".npz"), allow_pickle=False) as archive:
            reference = archive["delta"]
        try:
            result, execution = run_candidate(submission, instance)
        except (ValueError, OSError) as error:
            result = None
            execution = {"cpu_seconds": 0.0, "wall_seconds": 0.0, "error": "invalid submission: " + str(error)}
        report = {"case_id": case_id, "family": record["family"], "accepted": False, **execution}
        if result is not None:
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                measurement = metrics(instance, result["delta"], result["z"], reference)
            if all(np.isfinite(value) for value in measurement.values()):
                report.update(measurement)
                report["accepted"] = accepted(measurement)
            else:
                report["error"] = "nonfinite verification metrics"
        reports.append(report)
        print(json.dumps(report, allow_nan=False), file=sys.stderr, flush=True)
    family_rates = {}
    for family in POLICY["families"]:
        selected = [record for record in reports if record["family"] == family]
        family_rates[family] = sum(record["accepted"] for record in selected) / len(selected) if selected else 0.0
    score = min(family_rates.values())
    overall = sum(record["accepted"] for record in reports) / max(len(reports), 1)
    anchor_path = HIDDEN / "baseline_anchor.json"
    baseline = json.loads(anchor_path.read_text())["score"] if anchor_path.exists() else None
    if baseline is not None and (not 0 <= baseline <= 1 or baseline + POLICY["improvement_target"] > 1):
        raise ValueError("baseline plus required improvement is outside attainable score range")
    full = len(reports) == len(POLICY["families"]) * POLICY["cases_per_family"]
    success = full and baseline is not None and score >= POLICY["worst_family_target"]
    success = success and overall >= POLICY["overall_target"] and score >= baseline + POLICY["improvement_target"]
    reason = "all fixed quality, family, improvement, and resource gates met" if success else "fixed target not met"
    if not full:
        reason = "partial suite is diagnostic only"
    elif baseline is None:
        reason = "baseline anchor not yet sealed; diagnostic only"
    runtime = {"candidate_cpu_seconds_total": sum(record["cpu_seconds"] for record in reports),
               "candidate_cpu_seconds_max": max((record["cpu_seconds"] for record in reports), default=0.0),
               "candidate_wall_seconds_total": sum(record["wall_seconds"] for record in reports),
               "evaluator_wall_seconds": time.monotonic() - evaluation_started,
               "trusted_parent_cpu_seconds": time.process_time() - parent_started}
    resources = {key: POLICY[key] for key in ("cpu_seconds", "wall_seconds", "memory_mb", "threads")}
    return {"policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
            "complete_suite": full, "score": score, "overall": overall, "family_rates": family_rates,
            "core_score": overall, "worst_family_score": score, "passed": bool(success), "reason": reason,
            "runtime": runtime, "resources": resources,
            "baseline_score": baseline, "success": bool(success), "cases": reports}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--cases", nargs="*")
    args = parser.parse_args()
    report = evaluate(Path(args.submission), set(args.cases) if args.cases else None)
    Path(args.report).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, allow_nan=False))


if __name__ == "__main__":
    main()

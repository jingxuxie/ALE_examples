"""Evaluate a submission against frozen labels without importing reference code."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np

from metrics import aggregate, score, track_metrics


PRIVATE = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 90
MEMORY_GIB = 4
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
SANDBOX_HELPER = PRIVATE.parents[2] / "authoring/sandbox_exec.py"


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_arrays(path):
    if not path.is_file() or path.stat().st_size > MAX_OUTPUT_BYTES:
        raise ValueError("missing or oversized output NPZ")
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 16 or sum(entry.file_size for entry in archive.infolist()) > MAX_OUTPUT_BYTES:
            raise ValueError("oversized uncompressed NPZ")
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}


def submission_environment(scratch):
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(scratch / "home"),
            "TMPDIR": str(scratch), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def run_submission(entrypoint, input_path, output_path, participant, **limits):
    namespace = {"__file__": str(SANDBOX_HELPER), "__name__": "pilot01_sandbox_exec"}
    exec(compile(SANDBOX_HELPER.read_text(), str(SANDBOX_HELPER), "exec"), namespace)
    return namespace["run_submission"](entrypoint, input_path, output_path, participant, **limits)


def is_reference_submission(submission):
    return Path(submission).resolve() == (PRIVATE / "strong").resolve()


def execute(submission, case, scratch):
    if is_reference_submission(submission):
        return execute_reference(submission, case, scratch)
    output = scratch / "result.npz"
    execution = run_submission(
        entrypoint=submission / "solve.py", input_path=case, output_path=output,
        participant=PRIVATE.parent / "participant", timeout=TIMEOUT_SECONDS, memory_gib=MEMORY_GIB,
    )
    returncode = execution["returncode"]
    status = "ok" if returncode == 0 else "timeout" if returncode == 124 else "process_error"
    return {"status": status, "returncode": returncode, "runtime_seconds": execution["seconds"],
            "stderr_tail": execution["log_tail"], "peak_rss_kib": execution["peak_rss_kib"]}, output


def execute_reference(submission, case, scratch):
    staged = scratch / "input"
    shutil.copytree(case, staged)
    (scratch / "home").mkdir()
    output = scratch / "result.npz"
    command = [sys.executable, str(submission / "solve.py"), "--input", str(staged), "--output", str(output)]
    started = time.monotonic()
    status = "ok"
    returncode = None
    with (scratch / "stdout.log").open("wb") as stdout, (scratch / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=submission, env=submission_environment(scratch),
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            returncode = process.wait(timeout=TIMEOUT_SECONDS)
            if returncode:
                status = "process_error"
        except subprocess.TimeoutExpired:
            status = "timeout"
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    runtime = time.monotonic() - started
    with (scratch / "stderr.log").open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - 6000))
        error_tail = handle.read().decode(errors="replace")
    return {"status": status, "returncode": returncode, "runtime_seconds": runtime, "stderr_tail": error_tail}, output


def evaluate_case(submission, record):
    result = {"id": record["id"], "families": {}, "metrics": {}, "errors": []}
    expected_families = {"import": record["import_family"], "map": "cell_gauge"}
    case = PRIVATE / record["case"]
    reference = PRIVATE / record["reference"]
    if hash_file(reference) != record["reference_sha256"]:
        raise RuntimeError(f"Reference checksum mismatch: {record['id']}")
    for filename, expected_hash in record["input_sha256"].items():
        if hash_file(case / filename) != expected_hash:
            raise RuntimeError(f"Input checksum mismatch: {record['id']}/{filename}")
    expected = read_arrays(reference)
    temporary_parent = None if is_reference_submission(submission) else PRIVATE
    with tempfile.TemporaryDirectory(prefix="pilot01-eval-", dir=temporary_parent) as temporary:
        scratch = Path(temporary)
        try:
            execution, output = execute(submission, case, scratch)
        except OSError as error:
            execution = {"status": "launch_error", "runtime_seconds": 0.0, "stderr_tail": str(error), "returncode": None}
            output = scratch / "missing.npz"
        result.update(execution)
        actual = None
        if execution["status"] == "ok":
            try:
                actual = read_arrays(output)
            except (ValueError, OSError, KeyError, EOFError, zipfile.BadZipFile) as error:
                result["errors"].append(f"output: {error}")
                result["status"] = "invalid_output"
        else:
            result["errors"].append(execution["status"])
        for prefix, family in expected_families.items():
            family_result = {"score": 0.0, "error": None, "weak_error": record["weak_errors"][prefix], "metrics": {}, "errors": []}
            if actual is not None:
                try:
                    error, metrics = track_metrics(actual, expected, prefix)
                    family_result.update(error=error, metrics=metrics, score=score(error, record["weak_errors"][prefix]))
                    result["metrics"].update(metrics)
                except (KeyError, ValueError, TypeError, OverflowError) as error:
                    family_result["errors"].append(str(error))
                    result["errors"].append(f"{family}: {error}")
                    result["status"] = "partial_invalid_output"
            else:
                family_result["errors"].append("submission produced no usable output")
            result["families"][family] = family_result
    return result


def evaluate(submission, split):
    submission = Path(submission).resolve()
    manifest = json.loads((PRIVATE / "reference" / f"manifest_{split}.json").read_text())
    started = time.monotonic()
    per_case = [evaluate_case(submission, record) for record in manifest["cases"]]
    report = {"schema_version": 1, "split": split, "submission": str(submission),
              "reference_pin": manifest["reference_pin"], "per_case": per_case,
              "runtime_seconds": time.monotonic() - started,
              "scoring": "geometric mean of family means; per track 1/(1+9*error/weak_error)",
              "isolation": ("author-only reference validation; existing clean process environment"
                            if is_reference_submission(submission) else
                            "authoring/sandbox_exec.py: bwrap, /usr/bin/python3, no private references or network")}
    report.update(aggregate(per_case))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--split", choices=("test", "challenge", "confirmation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.split)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("split", "core_score", "worst_family_score", "family_scores")}))


if __name__ == "__main__":
    main()

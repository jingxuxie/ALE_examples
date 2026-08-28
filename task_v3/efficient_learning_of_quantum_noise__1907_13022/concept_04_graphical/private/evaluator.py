import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT.parent / "private"))
from evaluation_sandbox import restrict_solver


def score(prediction, target, baseline, groups):
    with np.errstate(over="ignore"):
        query_scores = 1.0 / (1.0 + 4.0 * (np.abs(prediction - target) / (np.abs(baseline - target) + 0.1)))
    grouped = {str(int(group)): float(np.mean(query_scores[groups == group])) for group in np.unique(groups)}
    return float(np.mean(list(grouped.values()))), grouped


def read_prediction(path, count):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise ValueError("Invalid output file")
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
        records = archive.infolist()
        if len(records) != 1 or records[0].filename != "log_event.npy" or records[0].file_size > 4096 + 8 * count:
            raise ValueError("Invalid output archive")
        payload = io.BytesIO(archive.read(records[0]))
    version = np.lib.format.read_magic(payload)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(payload)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(payload)
    else:
        raise ValueError("Unsupported NPY version")
    if shape != (count,) or dtype.kind != "f" or dtype.itemsize != 8:
        raise ValueError("Incorrect prediction schema")
    raw = payload.read()
    if len(raw) != 8 * count:
        raise ValueError("Incorrect payload length")
    prediction = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if not np.all(np.isfinite(prediction)) or np.any(prediction > 0):
        raise ValueError("Invalid log probabilities")
    return prediction


def child_limits(submission, staged_workdir):
    restrict_solver(submission.parent, staged_workdir, seconds=120, gibibytes=3)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**2, 4 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))


def execute(submission, input_path, query_count):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="graphical-case-") as temporary:
        staged = Path(temporary)
        code = staged / "code"
        staged_workdir = staged / "work"
        code.mkdir()
        staged_workdir.mkdir()
        (staged_workdir / "cache").mkdir()
        original_submission = submission
        submission = code / "solver.py"
        shutil.copyfile(original_submission, submission)
        staged_input = staged_workdir / "input.npz"
        staged_output = staged_workdir / "output.npz"
        shutil.copyfile(input_path, staged_input)
        environment = {
            "PATH": "/usr/bin:/bin", "HOME": str(staged_workdir), "TMPDIR": str(staged_workdir),
            "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1", "LANG": "C.UTF-8",
            "NUMBA_CACHE_DIR": str(staged_workdir / "cache"),
        }
        process = None
        status = "ok"
        try:
            process = subprocess.Popen(
                [sys.executable, "-I", str(submission), str(staged_input), str(staged_output)],
                cwd=staged_workdir, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                start_new_session=True, preexec_fn=lambda: child_limits(submission, staged_workdir),
            )
            process.wait(timeout=120)
            if process.returncode:
                status = "execution_failed"
        except subprocess.TimeoutExpired:
            status = "timeout"
        except subprocess.SubprocessError:
            status = "sandbox_failed"
        except OSError:
            status = "launch_failed"
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        prediction = None
        if status == "ok":
            try:
                prediction = read_prediction(staged_output, query_count)
            except (ValueError, OSError, EOFError, zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError, OverflowError, TypeError):
                status = "invalid_output"
        return prediction, status, time.monotonic() - started


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(submission, pool):
    if not submission.is_file() or submission.stat().st_size > 2 * 1024**2:
        raise ValueError("Submission must be one Python file no larger than 2 MiB")
    manifest = json.loads((ROOT / "private/reference/manifest.json").read_text())
    records = []
    started = time.monotonic()
    for entry in manifest["cases"]:
        if entry["pool"] != pool:
            continue
        input_path, truth_path = ROOT / entry["input"], ROOT / entry["truth"]
        if sha256(input_path) != entry["input_sha256"] or sha256(truth_path) != entry["truth_sha256"]:
            raise ValueError("Private corpus integrity check failed; regenerate the corpus")
        prediction, status, seconds = execute(submission, input_path, entry["queries"])
        value, grouped = 0.0, {}
        if status == "ok":
            with np.load(truth_path, allow_pickle=False) as truth:
                value, grouped = score(prediction, truth["target"], truth["baseline"], truth["event_group"])
        record = {"id": entry["id"], "family": entry["family"], "score": value, "groups": grouped, "status": status, "runtime": seconds}
        records.append(record)
    if not records:
        raise ValueError("Selected pool is empty")
    families = {}
    for family in sorted({record["family"] for record in records}):
        selected = [record["score"] for record in records if record["family"] == family]
        families[family] = {"score": float(np.mean(selected)), "cases": len(selected)}
    aggregate = float(np.mean([family["score"] for family in families.values()]))
    return {
        "version": 1, "pool": pool, "mean_core": aggregate if pool == "core" else None,
        "mean_challenge": aggregate if pool == "challenge" else None, "mean_selected": aggregate,
        "worst_family": min(family["score"] for family in families.values()),
        "families": families, "cases": records, "runtime": sum(record["runtime"] for record in records),
        "evaluator_wall": time.monotonic() - started, "submission_sha256": sha256(submission),
        "limits": {"wall_seconds_per_case": 120, "cpu_seconds_per_case": 120, "address_space_gib": 3},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--pool", choices=("core", "challenge"), default="core")
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = evaluate(arguments.submission.resolve(), arguments.pool)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("pool", "mean_core", "mean_challenge", "worst_family", "runtime")}, allow_nan=False))

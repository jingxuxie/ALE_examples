"""Score a solve.py CLI against precomputed, private official outputs."""

import argparse
import hashlib
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
import zipfile

for thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS"):
    os.environ[thread_variable] = "4"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "packing": ["packed"],
    "unpacking": ["unpacked", "unpacked_rfft"],
    "symmetry": ["mr", "mi", "asymmetry"],
    "transport": ["y", "reverse_y"],
    "density": ["log_density_y", "reverse_log_density"],
    "sensitivity": ["jvp_y", "jvp_log_density", "grad_x", "grad_theta"],
    "momenta": ["momenta", "lattice_momenta", "shell_squared"],
}
FAILURE_ERROR = 1e6
TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 128 * 1024**2
SANDBOX_PYTHON = "/task/input/runtime/bin/python3.12"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def load_archive(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("archive must be a regular file, not a symlink or special file")
    if path.stat().st_size > MAX_OUTPUT_BYTES:
        raise ValueError("output archive exceeds 128 MiB")
    with zipfile.ZipFile(path) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > MAX_OUTPUT_BYTES:
            raise ValueError("uncompressed output exceeds 128 MiB")
    with np.load(path, allow_pickle=False) as archive:
        return dict(archive)


def array_error(value, expected):
    if value is None:
        return FAILURE_ERROR
    value = np.asarray(value)
    if (value.shape != expected.shape or value.dtype.kind not in "biufc"
            or (not np.iscomplexobj(expected) and np.iscomplexobj(value))
            or not np.all(np.isfinite(value))):
        return FAILURE_ERROR
    dtype = np.complex128 if np.iscomplexobj(expected) else np.float64
    with np.errstate(over="ignore", invalid="ignore"):
        difference = np.abs(value.astype(dtype) - expected.astype(dtype))
        absolute = np.abs(expected.astype(dtype))
        maximum = np.max(difference)
        rms_difference = (maximum * np.sqrt(np.mean((difference / maximum)**2))
                          if maximum > 0 else 0.0)
        rms_reference = np.sqrt(np.mean(absolute**2))
        error = (rms_difference / max(1.0, float(rms_reference))
                 + maximum / max(1.0, float(np.max(absolute)))) / 2
    return float(error) if np.isfinite(error) else FAILURE_ERROR


def measure(outputs, expected):
    return {family: {key: array_error(outputs.get(key), expected[key]) for key in keys}
            for family, keys in FAMILIES.items()}


def family_errors(measurements):
    return {family: float(np.mean([np.mean(list(case[family].values()))
                                  for case in measurements]))
            for family in FAMILIES}


def score_errors(errors, weak_errors):
    result = {}
    for family, error in errors.items():
        weak = weak_errors[family]
        if weak <= 0:
            raise ValueError(f"degenerate weak calibration for {family}")
        skill = 1 - math.log1p(error / 1e-10) / math.log1p(weak / 1e-10)
        logit = (math.log(9) + math.log(19)) * skill - math.log(9)
        score = (1 / (1 + math.exp(-logit)) if logit >= 0
                 else math.exp(logit) / (1 + math.exp(logit)))
        result[family] = {"error": error, "weak_error": weak, "strong_error": 0.0,
                          "normalized_skill": skill, "score": score}
    return result


def runtime_python():
    candidates = [os.environ.get("ALE_PYTHON"),
                  ROOT / "participant/input/runtime/bin/python3.12",
                  "/tmp/ale_python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12",
                  sys.executable]
    return str(next(Path(candidate).resolve() for candidate in candidates
                    if candidate and Path(candidate).is_file()))


def child_environment(isolate=False, threads=4):
    environment = {} if isolate else os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "BIJX_SOURCE"):
        environment.pop(key, None)
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        environment[key] = str(threads)
    environment.update(JAX_ENABLE_X64="1", JAX_PLATFORMS="cpu", CUDA_VISIBLE_DEVICES="",
                       XLA_FLAGS="--xla_cpu_multi_thread_eigen=false",
                       PYTHONDONTWRITEBYTECODE="1")
    if isolate:
        environment.update(PATH="/task/input/runtime/bin:/usr/bin",
                           PYTHONPATH="/submission:/task/workspace",
                           HOME="/tmp", TMPDIR="/tmp", LANG="C.UTF-8",
                           PYTHONNOUSERSITE="1")
    return environment


def absolute_path_aliases(path):
    original = Path(os.path.abspath(path))
    aliases = {original, original.resolve()}
    for candidate in tuple(aliases):
        if candidate.is_relative_to("/srv/home"):
            counterpart = Path("/home") / candidate.relative_to("/srv/home")
        elif candidate.is_relative_to("/home"):
            counterpart = Path("/srv/home") / candidate.relative_to("/home")
        else:
            continue
        if counterpart.exists() and candidate.samefile(counterpart):
            aliases.add(counterpart)
    return sorted(aliases, key=str)


def isolated_paths(submission):
    participant = (ROOT / "participant").resolve()
    protected = [(ROOT / "private").resolve(),
                 (ROOT.parents[1] / "private").resolve(),
                 Path("/tmp/ale_bijx").resolve()]
    protected = [alias for secret in protected for alias in absolute_path_aliases(secret)]
    exposed_paths = [alias for source in (participant, submission)
                     for alias in absolute_path_aliases(source)]
    for exposed in exposed_paths:
        if any(exposed.is_relative_to(secret) or secret.is_relative_to(exposed)
               for secret in protected):
            raise ValueError("isolated mounts must not overlap private sources, references or pools; "
                             "use --no-isolate only for trusted reference checks")
    runtime = participant / "input/runtime/bin/python3.12"
    if not runtime.is_file() or not runtime.resolve().is_relative_to(participant):
        raise FileNotFoundError("isolation requires a self-contained public input/runtime/bin/python3.12")
    if not (submission / "solve.py").resolve().is_relative_to(submission.resolve()):
        raise ValueError("isolated solve.py must reside inside the submission directory")
    executable = shutil.which("bwrap")
    if executable is None:
        raise FileNotFoundError("bwrap is required for isolated submissions; no privileged fallback")
    return participant, executable


def isolated_command(submission, work, threads=4):
    participant, executable = isolated_paths(submission)
    command = [executable, "--die-with-parent", "--unshare-all", "--new-session",
               "--clearenv", "--cap-drop", "ALL"]
    for system_path in ("/usr", "/lib", "/lib64"):
        if Path(system_path).exists():
            command.extend(["--ro-bind", system_path, system_path])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(participant), "/task",
                    "--ro-bind", str(submission), "/submission",
                    "--bind", str(work), "/work", "--chdir", "/submission"])
    for source in (participant, submission):
        for alias in absolute_path_aliases(source):
            command.extend(["--ro-bind", str(source.resolve()), str(alias)])
    for key, value in child_environment(isolate=True, threads=threads).items():
        command.extend(["--setenv", key, value])
    command.extend(["--", SANDBOX_PYTHON, "/submission/solve.py",
                    "/work/input.npz", "/work/output.npz"])
    return command


def restrict_cores():
    if hasattr(os, "sched_getaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        preferred = [core for core in (36, 37, 38, 39) if core in allowed]
        selected = preferred if len(preferred) == 4 else allowed[:4]
        os.sched_setaffinity(0, selected)
        return selected
    return []


def evaluate(submission, pool="challenge", isolate=True):
    cores = restrict_cores()
    threads = min(4, len(cores)) if cores else 4
    submission = Path(os.path.abspath(submission))
    solution = submission / "solve.py"
    if not solution.is_file():
        raise FileNotFoundError(f"required submission entry point: {solution}")
    if isolate:
        isolated_paths(submission)
    pool_dir = ROOT / "private/challenge_pool"
    manifest = json.loads((pool_dir / "manifest.json").read_text())
    python = SANDBOX_PYTHON if isolate else runtime_python()
    records = []
    measurements = []
    scratch = ROOT / "private/.runs"
    scratch.mkdir(exist_ok=True)
    for case in manifest["pools"][pool]:
        input_path = pool_dir / case["input"]
        reference_path = pool_dir / case["reference"]
        if sha256(input_path) != case["input_sha256"] or sha256(reference_path) != case["reference_sha256"]:
            raise ValueError(f"pool integrity check failed: {case['name']}")
        expected = load_archive(reference_path)
        outputs = {}
        status = "ok"
        details = ""
        with tempfile.TemporaryDirectory(prefix="case_", dir=scratch) as temporary:
            temporary = Path(temporary)
            work = temporary / "io"
            work.mkdir()
            staged_input = work / "input.npz"
            output = work / "output.npz"
            log = temporary / "process.log"
            shutil.copyfile(input_path, staged_input)
            command = (isolated_command(submission, work, threads) if isolate
                       else [python, str(solution), str(staged_input), str(output)])
            environment = ({"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"} if isolate
                           else child_environment(threads=threads))
            started = time.perf_counter()
            with log.open("wb") as log_handle:
                process = subprocess.Popen(
                    command, cwd=work if isolate else submission,
                    env=environment, stdin=subprocess.DEVNULL, stdout=log_handle,
                    stderr=subprocess.STDOUT, start_new_session=True,
                    close_fds=True,
                )
                try:
                    process.wait(timeout=TIMEOUT_SECONDS)
                    if process.returncode:
                        status = "process_error"
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    status = "timeout"
            elapsed = time.perf_counter() - started
            if status == "ok":
                try:
                    outputs = load_archive(output)
                except Exception as error:
                    status = "invalid_archive"
                    details = str(error)
            if status != "ok":
                with log.open("rb") as handle:
                    details += handle.read(4096).decode(errors="replace")
        measured = measure(outputs, expected)
        measurements.append(measured)
        records.append({"name": case["name"], "geometry": case["geometry"],
                        "wall_seconds": elapsed, "status": status,
                        "details": details, "array_errors": measured})
    families = score_errors(family_errors(measurements), manifest["weak_errors"])
    return {
        "protocol": "fourier-transport-v1", "pool": pool, "submission": str(submission),
        "python": python, "score": float(np.mean([item["score"] for item in families.values()])),
        "normalized_skill_mean": float(np.mean([item["normalized_skill"] for item in families.values()])),
        "families": families, "cases": records,
        "wall_seconds_total": sum(case["wall_seconds"] for case in records),
        "wall_seconds_max": max(case["wall_seconds"] for case in records),
        "failures": sum(case["status"] != "ok" for case in records),
        "timeout_seconds_per_case": TIMEOUT_SECONDS,
        "isolated": isolate, "cpu_affinity": cores, "numerical_threads": threads,
        "isolation_note": ("bwrap: public task/submission and their verified original absolute-path "
                           "aliases read-only, current case I/O writable; "
                           "private pools, references and shared sources are not mounted; no network"
                           if isolate else "Explicit privileged execution for trusted reference checks only"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--pool", choices=["challenge"], default="challenge")
    parser.add_argument("--isolate", action=argparse.BooleanOptionalAction, default=True,
                        help="isolate submissions with bwrap (default); --no-isolate is for trusted references only")
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.pool, isolate=arguments.isolate)
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("score", "normalized_skill_mean", "failures", "wall_seconds_total")}))


if __name__ == "__main__":
    main()

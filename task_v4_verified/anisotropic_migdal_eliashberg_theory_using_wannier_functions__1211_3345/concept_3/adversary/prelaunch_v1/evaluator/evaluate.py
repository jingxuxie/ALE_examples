"""Trusted parent scorer; candidate code runs only in the shared sandbox."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "participant"
HIDDEN = ROOT / "evaluator" / "hidden"
DEFAULT_SANDBOX = ROOT / "evaluator" / "sandbox_adapter.py"


def target_configuration():
    raw = (HIDDEN / "target.json").read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def score(prediction, labels, family, configuration):
    expected_shape = labels.shape
    if prediction.shape != expected_shape:
        raise ValueError(f"wrong shape: expected {expected_shape}, received {prediction.shape}")
    if prediction.dtype.kind not in "fiu" or not np.isfinite(prediction).all():
        raise ValueError("output must be finite and real numeric")
    if np.any(prediction < 0) or np.any(prediction > 1):
        raise ValueError("spectral weights outside [0,1]")
    if np.max(np.abs(prediction.sum(axis=-1) - 1)) > configuration["normalization_tolerance"]:
        raise ValueError("spectral weights are not normalized")
    scales = np.asarray(configuration["absolute_mass_scales"])
    errors = np.sqrt(np.mean(((prediction - labels) / scales) ** 2, axis=(1, 2)))
    grouped = {name: float(np.mean(errors[family == index]))
               for index, name in enumerate(configuration["families"]) if np.any(family == index)}
    core = float(np.mean(errors))
    worst = max(grouped.values())
    tail = float(np.quantile(errors, .9))
    return dict(core=core, worst_family=worst, case_p90=tail, family_errors=grouped,
                absolute_mass_rmse=float(np.sqrt(np.mean((prediction - labels) ** 2))),
                passed=bool(core <= configuration["core_max"] and worst <= configuration["worst_family_max"]
                            and tail <= configuration["case_p90_max"]))


def read_prediction(path, maximum_bytes):
    if path.is_symlink() or path.resolve().parent != path.parent.resolve():
        raise ValueError("output must resolve directly inside scratch, not through a symlink")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum_bytes:
            raise ValueError("output must be a small regular file")
        with zipfile.ZipFile(stream) as compressed:
            entries = compressed.infolist()
            if len(entries) != 1 or entries[0].filename != "spectral_mass.npy":
                raise ValueError("output must contain exactly spectral_mass")
            if entries[0].file_size > maximum_bytes:
                raise ValueError("decompressed output is too large")
        stream.seek(0)
        with np.load(stream, allow_pickle=False) as archive:
            return archive["spectral_mass"].copy()


def child_limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2,) * 2)


def evaluate(candidate, split="hidden", runner=DEFAULT_SANDBOX, keep_scratch=False):
    configuration, target_hash = target_configuration()
    manifest = json.loads((HIDDEN / "data_manifest.json").read_text())
    if manifest["target_sha256"] != target_hash:
        raise ValueError("frozen target hash mismatch")
    candidate = Path(candidate).resolve()
    if not (candidate / "solve.py").is_file():
        raise ValueError("candidate directory must contain solve.py")
    if not Path(runner).is_file():
        raise FileNotFoundError("Shared sandbox missing; refusing unisolated candidate execution")
    if candidate == ROOT or candidate in HIDDEN.parents or HIDDEN == candidate or candidate in PUBLIC.parents:
        raise ValueError("submission cannot expose a private ancestor")
    for entry in candidate.rglob("*"):
        if entry.is_symlink():
            raise ValueError("submission symlinks are not accepted")
    feature_path = HIDDEN / "test_features.npz" if split == "hidden" else PUBLIC / "input" / "validation_features.npz"
    label_path = HIDDEN / "test_labels.npz" if split == "hidden" else PUBLIC / "input" / "validation_labels.npz"
    with np.load(feature_path, allow_pickle=False) as archive:
        features = {key: archive[key].copy() for key in archive.files}
    with np.load(label_path, allow_pickle=False) as archive:
        labels = archive["spectral_mass"].copy()
        families = archive["family"].copy()
    scratch_parent = ROOT / "attempts" / ".scratch"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="candidate_", dir=scratch_parent)
    scratch = Path(temporary.name)
    input_path, output_path = scratch / "features.npz", scratch / "prediction.npz"
    np.savez_compressed(input_path, **features)
    command = [sys.executable, str(Path(runner).resolve()), "--submission", str(candidate),
               "--participant", str(PUBLIC), "--input", str(input_path), "--output", str(output_path),
               "--scratch", str(scratch), "--cpu-seconds", str(configuration["cpu_seconds"]),
               "--memory-mb", str(configuration["address_space_gib"] * 1024)]
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    environment.update({name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
    result = dict(valid=False, passed=False, split=split, target_sha256=target_hash)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    try:
        with (scratch / "stdout.log").open("wb") as stdout, (scratch / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, cwd=scratch, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True, close_fds=True,
                                       preexec_fn=child_limits)
            try:
                returncode = process.wait(timeout=configuration["wall_seconds"])
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise ValueError("wall ceiling exceeded")
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        result.update(cpu_seconds=cpu, wall_seconds=time.monotonic() - started, returncode=returncode)
        if returncode != 0:
            raise ValueError(f"candidate exited with status {returncode}")
        if cpu > configuration["cpu_seconds"] + .25:
            raise ValueError("CPU limit exceeded")
        prediction = read_prediction(output_path, configuration["output_max_bytes"])
        result.update(score(prediction, labels, families, configuration), valid=True)
    except (ValueError, OSError, EOFError, zipfile.BadZipFile, KeyError, TypeError) as error:
        result.update(error=str(error), wall_seconds=time.monotonic() - started)
    finally:
        if keep_scratch:
            temporary._finalizer.detach()
            result["scratch"] = str(scratch)
        else:
            temporary.cleanup()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "hidden"), default="hidden")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--sandbox-runner", type=Path, default=DEFAULT_SANDBOX)
    parser.add_argument("--keep-scratch", action="store_true")
    arguments = parser.parse_args()
    result = evaluate(arguments.candidate, arguments.split, arguments.sandbox_runner, arguments.keep_scratch)
    text = json.dumps(result, indent=2, allow_nan=False)
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

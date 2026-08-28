from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = dict(vector_field=.15, divergence=.20, conditional_derivative=.20, geometry=.15, forward=.15, reverse=.15)


def runtime():
    bundled = ROOT / "participant" / "input" / "runtime"
    for path in (bundled / "bin" / "python3.12", bundled / "bin" / "python3"):
        if path.is_file():
            return path
    matches = sorted(bundled.glob("*/bin/python3.12"))
    return matches[0] if matches else Path(sys.executable)


def environment():
    result = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        result[key] = "4"
    result.update(ALE_INPUT_DIR=str(ROOT / "participant" / "input"), JAX_ENABLE_X64="true", JAX_PLATFORMS="cpu", PYTHONDONTWRITEBYTECODE="1")
    result["XLA_FLAGS"] = "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4"
    return result


def launch_command(submission, staging, trusted_reference=False):
    public = ROOT / "participant"
    interpreter = "/task/" + str(runtime().relative_to(public))
    command = ["bwrap", "--die-with-parent", "--unshare-all", "--new-session",
               "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
               "--ro-bind", "/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--ro-bind", str(public), "/task",
               "--ro-bind", str(submission), "/submission", "--bind", str(staging), "/work"]
    for source in (public, submission):
        aliases = {str(source), str(source.resolve())}
        for original in tuple(aliases):
            if original.startswith("/home/"):
                aliases.add("/srv" + original)
            elif original.startswith("/srv/home/"):
                aliases.add(original.removeprefix("/srv"))
        for destination in sorted(aliases):
            command += ["--ro-bind", str(source), destination]
    entry, working = "/submission/solve.py", "/submission"
    if trusted_reference:
        if submission not in (ROOT / "attempt" / "strong", ROOT / "attempt" / "frozen"):
            raise ValueError("Trusted reference mode is restricted to the two private oracle wrappers")
        reference = ROOT / "private" / "reference"
        working = "/pilot/attempt/" + submission.name
        entry = working + "/solve.py"
        command += ["--ro-bind", str(submission), working,
                    "--ro-bind", str(reference / "author.py"), "/pilot/private/reference/author.py",
                    "--ro-bind", str(reference / "vendor"), "/pilot/private/reference/vendor",
                    "--ro-bind", str(public / "input"), "/pilot/participant/input"]
    command += ["--chdir", working, "--clearenv"]
    settings = dict(PATH="/task/input/runtime/bin:/usr/bin:/bin", HOME="/tmp", PYTHONPATH="/submission:/task/workspace",
                    ALE_INPUT_DIR="/task/input", JAX_ENABLE_X64="true", JAX_PLATFORMS="cpu", PYTHONDONTWRITEBYTECODE="1",
                    OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4", NUMEXPR_NUM_THREADS="4",
                    XLA_FLAGS="--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4")
    for name, value in settings.items():
        command += ["--setenv", name, value]
    return command + ["--", "/usr/bin/taskset", "-c", "40-43", interpreter, entry, "/work/input.npz", "/work/output.npz"]


def specifications(record):
    operation = record["operation"]
    if operation != "probe":
        return {"phi": (operation, 2e-4, 1e-3), "logp": (operation, 2e-4, 1.)}
    result = {"velocity": ("vector_field", 2e-5, 1e-3), "divergence": ("divergence", 2e-5, 1.), "kernel": ("geometry", 2e-5, 1e-3)}
    if record["model"].startswith("range"):
        result.update(dlam_velocity=("conditional_derivative", 2e-5, 1e-3), dlam_divergence=("conditional_derivative", 2e-5, 1.))
    return result


def numerical_quality(actual, expected, tolerance, floor):
    if actual.shape != expected.shape or actual.dtype.kind != "f" or not np.isfinite(actual).all():
        return 0., None
    difference = actual - expected
    rms_error = float(np.sqrt(np.mean(difference * difference))) / max(float(np.sqrt(np.mean(expected * expected))), floor)
    max_error = float(np.max(np.abs(difference))) / max(float(np.max(np.abs(expected))), floor)
    relative = .5 * (rms_error + max_error)
    if not np.isfinite(relative):
        return 0., None
    return 1 / (1 + relative / tolerance), relative


def evaluate(submission, report_path, pool, trusted_reference=False, calibrate_reference=False, reference_steps=100):
    if reference_steps != 100 and (trusted_reference or calibrate_reference):
        raise ValueError("Refined-oracle diagnostics require ordinary frozen submission execution")
    if not (submission / "solve.py").is_file():
        raise ValueError("Submission directory must contain solve.py")
    folder = ROOT / "private" / ("reference/cases" if pool == "test" else "challenge_pool")
    manifest = json.loads((folder / "manifest.json").read_text())
    if calibrate_reference and submission != ROOT / "attempt" / "strong":
        raise ValueError("Only the actual author solver can calibrate runtime")
    trusted_reference = trusted_reference or calibrate_reference
    rows, grouped, accurate = [], defaultdict(list), defaultdict(list)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scalar-eval-", dir=report_path.parent) as temporary:
        staging = Path(temporary)
        for record in manifest["cases"]:
            for name in ("input", "expected"):
                source = folder / record[name]
                checksum = hashlib.sha256(source.read_bytes()).hexdigest()
                if checksum != record[name + "_sha256"]:
                    raise ValueError("Reference integrity failure: " + str(source))
            request = dict(np.load(folder / record["input"], allow_pickle=False))
            expected_path = folder / record["expected"]
            if reference_steps != 100 and record["operation"] != "probe":
                expected_path = ROOT / "private/reference/refined" / pool / f'{record["id"]}.{reference_steps}.npz'
            expected = dict(np.load(expected_path, allow_pickle=False))
            input_path, output_path = staging / "input.npz", staging / "output.npz"
            np.savez(input_path, **request)
            if output_path.exists():
                output_path.unlink()
            limit = max(60., 3. * record["reference_seconds"])
            started = time.perf_counter()
            status, message, output = "ok", "", {}
            with (staging / "stderr.txt").open("w+") as errors:
                process = subprocess.Popen(launch_command(submission, staging, trusted_reference),
                                           cwd=submission, env=environment(), stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=errors, start_new_session=True)
                try:
                    returncode = process.wait(timeout=limit)
                    if returncode:
                        status = "error"
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    status = "timeout"
                elapsed = time.perf_counter() - started
                errors.seek(0)
                message = errors.read()[-3000:]
            if status == "error" and message.startswith("bwrap:"):
                raise RuntimeError("Isolation infrastructure failed; launch outside the parent sandbox: " + message)
            if status == "ok":
                try:
                    if output_path.is_symlink() or not output_path.is_file():
                        raise ValueError("Output must be a regular NPZ file, not a symlink")
                    with np.load(output_path, allow_pickle=False) as archive:
                        output = dict(archive)
                except Exception as error:
                    status, message = "invalid_output", str(error)
            if calibrate_reference:
                if status != "ok":
                    raise RuntimeError("Isolated author calibration failed: " + message)
                for key, (_, tolerance, floor) in specifications(record).items():
                    if key not in output or numerical_quality(output[key], expected[key], tolerance, floor)[0] < .99:
                        raise RuntimeError("Author calibration disagrees with stored reference: " + key)
                record.setdefault("unisolated_reference_seconds", record["reference_seconds"])
                record["reference_seconds"] = elapsed
                record["reference_environment"] = "public runtime; bwrap; actual author execution; no answer mounts"
            factor = 1 / (1 + .03 * elapsed / record["reference_seconds"])
            scores = {}
            for key, (group, tolerance, floor) in specifications(record).items():
                quality, relative = 0., None
                if status == "ok" and key in output:
                    actual, target = output[key], expected[key]
                    if key == "logp" and actual.shape == target.shape:
                        actual, target = actual - request["logp"], target - request["logp"]
                    quality, relative = numerical_quality(actual, target, tolerance, floor)
                grouped[group].append(quality * factor)
                accurate[group].append(quality)
                scores[key] = dict(group=group, relative_error=relative, accuracy=quality, score=quality * factor)
            row = dict(id=record["id"], model=record["model"], size=record["size"], profile=record["profile"], operation=record["operation"],
                       status=status, seconds=elapsed, reference_seconds=record["reference_seconds"], timeout_seconds=limit,
                       runtime_factor=factor, outputs=scores,
                       oracle_sha256=hashlib.sha256(expected_path.read_bytes()).hexdigest())
            if message:
                row["stderr_tail"] = message
            rows.append(row)
            print(record["id"], status, round(elapsed, 3), flush=True)
    groups = {name: dict(weight=weight, score=float(np.mean(grouped[name])), accuracy=float(np.mean(accurate[name]))) for name, weight in WEIGHTS.items()}
    report = dict(pool=pool, score=sum(WEIGHTS[name] * groups[name]["score"] for name in WEIGHTS), groups=groups,
                  cases=rows, python=str(runtime()), cores=[40, 41, 42, 43], threads=4,
                  timing="end-to-end wall time; fresh isolated process; machine-local precomputed denominator",
                  isolated=True, trusted_reference=trusted_reference, calibrated_reference=calibrate_reference,
                  timeout_floor_seconds=60, reference_steps=reference_steps,
                  diagnostic_only=reference_steps != 100,
                  timing_reference_steps=100)
    if calibrate_reference:
        temporary_manifest = folder / "manifest.json.tmp"
        temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary_manifest.replace(folder / "manifest.json")
    anchor_path = ROOT / "private" / "reference" / "empirical_anchors.json"
    if anchor_path.exists() and reference_steps == 100:
        anchors = json.loads(anchor_path.read_text()).get(pool)
        if anchors:
            report["empirical_anchors"] = anchors
            report["weak_strong_normalized_score"] = (report["score"] - anchors["weak_score"]) / (anchors["strong_score"] - anchors["weak_score"])
            report["normalization"] = "(score - measured weak)/(measured strong - measured weak), without clipping; primary score unchanged"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"score": report["score"], "groups": groups}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--pool", choices=("test", "challenge"), default="test")
    parser.add_argument("--trusted-reference", action="store_true")
    parser.add_argument("--calibrate-reference", action="store_true")
    parser.add_argument("--reference-steps", type=int, choices=(100, 400), default=100)
    args = parser.parse_args()
    evaluate(args.submission.resolve(), args.report.resolve(), args.pool, args.trusted_reference, args.calibrate_reference, args.reference_steps)


if __name__ == "__main__":
    main()

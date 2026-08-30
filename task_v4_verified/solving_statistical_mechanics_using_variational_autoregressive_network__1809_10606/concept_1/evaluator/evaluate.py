import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import tempfile
import time

import numpy as np
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT.parent / "authoring" / "isolation" / "bwrap"
LIMIT = 120
TARGET = {"mean_kl": 0.12, "worst_family_kl": 0.20, "baseline_ratio": 0.40, "minimum_ess": 0.25}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def parse(raw):
    def reject(value):
        raise ValueError("nonfinite_json_number")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def validate_model(model, count):
    if not isinstance(model, dict) or set(model) != {"mixing", "weights", "biases", "orders"}:
        raise ValueError("model_schema")
    mixing = np.asarray(model["mixing"], dtype=float)
    if mixing.ndim != 1 or not 1 <= len(mixing) <= 8:
        raise ValueError("component_count")
    components = len(mixing)
    weights = np.asarray(model["weights"], dtype=float)
    biases = np.asarray(model["biases"], dtype=float)
    orders = np.asarray(model["orders"])
    if weights.shape != (components, count, count) or biases.shape != (components, count) or orders.shape != (components, count):
        raise ValueError("parameter_shapes")
    if any(not np.isfinite(array).all() for array in (mixing, weights, biases)):
        raise ValueError("nonfinite_parameters")
    if np.any(mixing <= 0) or abs(mixing.sum() - 1) > 1e-10:
        raise ValueError("mixing_normalization")
    if orders.dtype.kind not in "iu" or any(sorted(order.tolist()) != list(range(count)) for order in orders):
        raise ValueError("causal_permutation")
    for matrix, order in zip(weights, orders):
        if np.any(np.triu(matrix[np.ix_(order, order)]) != 0):
            raise ValueError("noncausal_weight")
    if np.any(np.abs(weights).sum(axis=2) + np.abs(biases) > 60 + 1e-12):
        raise ValueError("conditional_bound")
    return mixing, weights, biases


def exact_score(instance, model):
    count = instance["n"]
    mixing, weights, biases = validate_model(model, count)
    couplings, fields = np.asarray(instance["couplings"]), np.asarray(instance["fields"])
    total = 1 << count
    log_target = np.empty(total)
    log_model = np.empty(total)
    for start in range(0, total, 16384):
        stop = min(total, start + 16384)
        integers = np.arange(start, stop, dtype=np.uint32)
        spins = 2.0 * ((integers[:, None] >> np.arange(count)) & 1) - 1
        potential = spins @ fields
        for left in range(count):
            for right in range(left):
                potential += couplings[left, right] * spins[:, left] * spins[:, right]
        log_target[start:stop] = potential
        component_logs = []
        for weight, bias, mass in zip(weights, biases, mixing):
            logits = spins @ weight.T + bias
            component_logs.append(np.log(mass) + ((spins > 0) * logits - np.logaddexp(0, logits)).sum(axis=1))
        log_model[start:stop] = logsumexp(component_logs, axis=0)
    log_partition = float(logsumexp(log_target))
    log_target -= log_partition
    log_norm = float(logsumexp(log_model))
    if abs(log_norm) > 1e-9:
        raise ValueError("joint_normalization")
    kl = float(np.exp(log_model) @ (log_model - log_target))
    ess = float(np.exp(-logsumexp(2 * log_target - log_model)))
    if not math.isfinite(kl) or kl < -1e-8 or not 0 < ess <= 1 + 1e-8:
        raise ValueError("numerical_scoring_failure")
    return {"kl": max(0, kl), "ess": min(1, ess), "log_norm": log_norm, "log_partition": log_partition}


def safe_read(path, maximum=1048576):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > maximum:
            raise ValueError("unsafe_or_oversized_artifact")
        return stream.read(maximum + 1)


def restrict_resources():
    available = sorted(os.sched_getaffinity(0))
    start = (os.getpid() * 4) % len(available)
    os.sched_setaffinity(0, {available[(start + offset) % len(available)] for offset in range(min(4, len(available)))})
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (480, 481))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def validate_submission(submission):
    submission = Path(submission).resolve(strict=True)
    if not (submission / "solve.py").is_file():
        raise ValueError("missing_solve.py")
    for private in (ROOT / "evaluator", ROOT / "adversary", ROOT.parent / "authoring"):
        private = private.resolve()
        if private == submission or private in submission.parents or submission in private.parents:
            raise ValueError("submission_overlaps_private_tree")
    for path in submission.rglob("*"):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1):
            raise ValueError("submission_links_forbidden")
        if not stat.S_ISREG(metadata.st_mode) and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("submission_special_file")
    return submission


def run_case(submission, instance, identifier):
    runtime = ROOT / "attempts" / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=identifier + "_", dir=runtime) as temporary:
        scratch = Path(temporary).resolve()
        (scratch / "instance.json").write_text(json.dumps(instance))
        command = [sys.executable, str(TRANSPORT), "--tmpfs", "/"]
        for path in ("/usr", "/bin", "/lib", "/lib64", "/etc/ld.so.cache", str(submission), str(ROOT / "participant")):
            if Path(path).exists():
                command.extend(["--ro-bind", path, path])
        command.extend(["--dev", "/dev", "--bind", str(scratch), str(scratch), "--", sys.executable,
                        "-u", str(submission / "solve.py"), str(scratch / "instance.json"), str(scratch / "model.json")])
        environment = {"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch), "LANG": "C.UTF-8",
                       "PYTHONPATH": str(ROOT / "participant" / "workspace"), "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONNOUSERSITE": "1", "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "4",
                       "OMP_THREAD_LIMIT": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"}
        began = time.monotonic()
        with (scratch / "stdout.log").open("wb") as stdout, (scratch / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, cwd=scratch, env=environment, stdout=stdout, stderr=stderr,
                                       start_new_session=True, preexec_fn=restrict_resources)
            try:
                process.wait(timeout=LIMIT)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise ValueError("wall_timeout")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        elapsed = time.monotonic() - began
        if process.returncode:
            raise ValueError("solver_exit_" + str(process.returncode) + ":" + (scratch / "stderr.log").read_text(errors="replace")[-1200:])
        model = parse(safe_read(scratch / "model.json"))
        return model, elapsed


def evaluate(submission, calibrate=False):
    submission = validate_submission(submission)
    manifest = parse((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    records = []
    for case in manifest["cases"]:
        record = {"id": case["id"], "family": case["family"], "valid": False, "reason": "not_run"}
        try:
            raw = (ROOT / "evaluator" / "hidden" / case["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != case["sha256"]:
                raise ValueError("hidden_data_hash_mismatch")
            instance = parse(raw)
            model, seconds = run_case(submission, instance, case["id"])
            record.update(exact_score(instance, model), wall_seconds=seconds, valid=True, reason="scored")
            if calibrate:
                case["baseline_kl"] = record["kl"]
                case["baseline_ess"] = record["ess"]
                case["baseline_model"] = model
            print(json.dumps(record), flush=True, file=sys.stderr)
        except Exception as error:
            record["reason"] = type(error).__name__ + ":" + str(error)
        records.append(record)
    valid = all(record["valid"] for record in records)
    if calibrate and valid:
        (ROOT / "evaluator" / "hidden" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    result = {"valid": valid, "passed": False, "core_score": 0.0, "worst_family_score": 0.0,
              "runtime_resource_score": 0.0, "targets": TARGET, "cases": records,
              "reason": "invalid_or_failed_case", "suite_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()}
    if not valid:
        return result
    families = {family: float(np.mean([record["kl"] for record in records if record["family"] == family]))
                for family in sorted({record["family"] for record in records})}
    mean = float(np.mean([record["kl"] for record in records]))
    worst = max(families.values())
    minimum_ess = min(record["ess"] for record in records)
    baseline = float(np.mean([case["baseline_kl"] for case in manifest["cases"]]))
    ratio = mean / max(1e-12, baseline)
    passed = mean <= TARGET["mean_kl"] and worst <= TARGET["worst_family_kl"] and ratio <= TARGET["baseline_ratio"] and minimum_ess >= TARGET["minimum_ess"]
    result.update(passed=bool(passed), core_score=1 / (1 + mean), worst_family_score=1 / (1 + worst),
                  runtime_resource_score=max(0.0, 1 - max(record["wall_seconds"] for record in records) / LIMIT),
                  mean_kl=mean, family_kl=families, worst_family_kl=worst, minimum_ess=minimum_ess,
                  baseline_mean_kl=baseline, baseline_ratio=ratio,
                  reason="all_fixed_targets_met" if passed else "quality_or_worst_family_or_tail_target_missed")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--calibrate-baseline", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.calibrate_baseline and Path(arguments.submission).resolve() != (ROOT / "participant" / "baseline").resolve():
            raise ValueError("calibration_only_for_supplied_baseline")
        report = evaluate(arguments.submission, arguments.calibrate_baseline)
    except Exception as error:
        report = {"core_score": 0, "worst_family_score": 0, "runtime_resource_score": 0,
                  "valid": False, "passed": False, "reason": type(error).__name__ + ":" + str(error)}
    Path(arguments.report).write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, allow_nan=False))


if __name__ == "__main__":
    main()

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import tempfile
import time

import numpy as np

from independent import checked_field, energy_gradient, lower_bound, read_case

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator/hidden"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "authoring"))
try:
    from sandbox import Sandbox
except ImportError:
    Sandbox = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_references():
    release_path = ROOT / "evaluator/release_manifest.json"
    if release_path.exists():
        release = read_case(release_path)
        for group in ("participant", "evaluator"):
            for relative, expected in release[group]["files"].items():
                if digest(ROOT / relative) != expected:
                    raise ValueError("release integrity failure: " + relative)
    target = read_case(HIDDEN / "target.json")
    manifest = read_case(HIDDEN / "manifest.json")
    for relative, expected in manifest["immutable_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("frozen asset integrity failure: " + relative)
    records = manifest["cases"]
    if len(records) != target["case_count"] or len({record["case_id"] for record in records}) != len(records):
        raise ValueError("invalid reference case set")
    family_counts = {family: sum(record["family"] == family for record in records) for family in target["families"]}
    if set(record["family"] for record in records) != set(target["families"]) or set(family_counts.values()) != {2}:
        raise ValueError("invalid family balance")
    for record in records:
        case = read_case(ROOT / record["case_path"])
        for kind in ("baseline", "witness"):
            field = checked_field(ROOT / record[kind + "_path"], case, target["result_max_bytes"])
            energy, unused, rms = energy_gradient(case, field)
            if abs(energy - record[kind + "_energy"]) > 1e-9:
                raise ValueError("reference energy mismatch")
            if rms > target["stationarity_rms_max"] or energy < lower_bound(case) - 1e-8:
                raise ValueError("invalid reference field")
        if record["baseline_energy"] - record["witness_energy"] < target["minimum_reference_gap"]:
            raise ValueError("reference gap too small")
    return target, records


def score_field(reference, case, field, elapsed, target):
    energy, unused, rms = energy_gradient(case, field)
    baseline = reference["baseline_energy"]
    witness = reference["witness_energy"]
    raw_closure = (baseline - energy) / (baseline - witness)
    reasons = []
    if not np.isfinite(energy) or not np.isfinite(rms):
        reasons.append("nonfinite independent energy or gradient")
    if not np.isfinite(elapsed) or elapsed < 0 or elapsed > target["wall_seconds_per_case"]:
        reasons.append("wall deadline exceeded or invalid trusted timing")
    if rms > target["stationarity_rms_max"]:
        reasons.append("gradient RMS exceeds 0.002")
    if energy < lower_bound(case) - 1e-8:
        reasons.append("energy below rigorous onsite lower bound")
    if energy > baseline + target["regression_relative_tolerance"] * max(1, abs(baseline)):
        reasons.append("energy regression against frozen baseline")
    valid = not reasons
    return {
        "case_id": reference["case_id"], "family": reference["family"],
        "valid": valid, "checked_energy": energy, "gradient_rms": rms,
        "raw_gap_closure": raw_closure, "case_score": float(np.clip(raw_closure, 0, 1)) if valid else 0.0,
        "wall_seconds": elapsed,
        "runtime_score": max(0.0, 1 - elapsed / target["wall_seconds_per_case"]) if valid else 0.0,
        "reason": "; ".join(reasons) if reasons else "ok",
    }


def invalid_case(reference, reason, elapsed=0.0):
    return {"case_id": reference["case_id"], "family": reference["family"], "valid": False, "case_score": 0.0, "runtime_score": 0.0, "wall_seconds": elapsed, "reason": reason}


def aggregate(records, target):
    if len(records) != target["case_count"] or len({record["case_id"] for record in records}) != len(records):
        raise ValueError("all unique cases must contribute")
    family_scores = {}
    for family in target["families"]:
        members = [record["case_score"] for record in records if record["family"] == family]
        if len(members) != 2:
            raise ValueError("all families require two cases")
        family_scores[family] = float(np.mean(members))
    core = float(np.mean(list(family_scores.values())))
    worst_family = min(family_scores, key=family_scores.get)
    worst = family_scores[worst_family]
    reasons = [record["case_id"] + ": " + record["reason"] for record in records if not record["valid"]]
    if core < target["core_min"]:
        reasons.append("core_score below 0.65")
    if worst < target["worst_family_min"]:
        reasons.append("worst_family_score below 0.45")
    return {"verification_mode": "A_BASELINE_IMPROVEMENT", "valid": all(record["valid"] for record in records), "status": "failed" if reasons else "passed", "core_score": core, "worst_family": worst_family, "worst_family_score": worst, "family_scores": family_scores, "runtime_score": float(np.mean([record["runtime_score"] for record in records])), "passed": not reasons, "reason": "; ".join(reasons) if reasons else "all frozen energy, stationarity, and resource goals met", "cases": records}


def scratch_usage(path, maximum_entries=4096):
    total = 0
    entries = 0
    for directory, subdirectories, filenames in os.walk(path, followlinks=False):
        entries += len(subdirectories) + len(filenames)
        if entries > maximum_entries:
            raise ValueError("scratch entry limit exceeded")
        for filename in filenames:
            try:
                metadata = os.lstat(Path(directory) / filename)
            except FileNotFoundError:
                continue
            if stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
    return total


if Sandbox is not None:
    class LimitedSandbox(Sandbox):
        def command(self, arguments):
            command = super().command(arguments)
            index = command.index("--tmpfs")
            if command[index + 1] != "/tmp":
                raise RuntimeError("unsupported sandbox helper layout")
            command[index:index + 2] = ["--bind", str(self.output), "/tmp"]
            return command

        def limits(self):
            super().limits()
            resource.setrlimit(resource.RLIMIT_CPU, (self.seconds, self.seconds))
            available = os.sched_getaffinity(0)
            os.sched_setaffinity(0, {min(available)})

        def stop(self):
            if self.process is not None:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait()


def run_case(submission, reference, target, capture_dir=None):
    if Sandbox is None:
        raise RuntimeError("trusted authoring/sandbox.py unavailable; refusing unsandboxed execution")
    case = read_case(ROOT / reference["case_path"])
    with tempfile.TemporaryDirectory(prefix="gl-public-case-") as temporary:
        staging = Path(temporary)
        public_input = staging / "input"
        public_input.mkdir()
        (public_input / "case.json").write_text(json.dumps(case, separators=(",", ":")))
        with LimitedSandbox(ROOT / "participant", submission, input_dir=public_input, seconds=int(target["wall_seconds_per_case"]), memory_gib=target["memory_mib"] // 1024) as sandbox:
            started = time.monotonic()
            reason = None
            log_path = staging / "solver.log"
            with log_path.open("wb") as log:
                process = sandbox.start(["/usr/bin/python3", "/submission/solve.py", "--input", "/input/case.json", "--output", "/output/result.npz"], stdout=log, stderr=log)
                while process.poll() is None:
                    if time.monotonic() - started > target["wall_seconds_per_case"]:
                        reason = "wall deadline exceeded"
                        sandbox.stop()
                        break
                    try:
                        usage = scratch_usage(sandbox.output) + log_path.stat().st_size
                        if usage > target["scratch_mib"] * 1024**2:
                            raise ValueError("scratch/log byte limit exceeded")
                    except ValueError as error:
                        reason = str(error)
                        sandbox.stop()
                        break
                    time.sleep(0.02)
                elapsed = time.monotonic() - started
                sandbox.stop()
            if reason is None and process.returncode != 0:
                reason = "nonzero exit: " + str(process.returncode)
            try:
                if reason is None and scratch_usage(sandbox.output) + log_path.stat().st_size > target["scratch_mib"] * 1024**2:
                    reason = "scratch/log byte limit exceeded"
            except ValueError as error:
                reason = str(error)
            if reason:
                record = invalid_case(reference, reason, elapsed)
                with log_path.open("rb") as log:
                    record["diagnostic"] = log.read(2048).decode("utf-8", "replace")
                return record
            try:
                field = checked_field(sandbox.output / "result.npz", case, target["result_max_bytes"])
                if capture_dir is not None:
                    destination = Path(capture_dir)
                    destination.mkdir(parents=True, exist_ok=True)
                    np.savez_compressed(destination / (reference["case_id"] + ".npz"), psi=field)
                return score_field(reference, case, field, elapsed, target)
            except Exception as error:
                return invalid_case(reference, "invalid output: " + str(error)[:300], elapsed)


def main():
    parser = argparse.ArgumentParser(description="Private energy-checked baseline-improvement evaluation")
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        target, references = load_references()
        submission = args.submission.resolve()
        if not (submission / "solve.py").is_file():
            raise ValueError("submission must contain solve.py")
        if submission == ROOT or ROOT.is_relative_to(submission) or (ROOT / "evaluator").is_relative_to(submission):
            raise ValueError("submission directory would expose private evaluator assets")
        records = []
        for reference in references:
            try:
                records.append(run_case(submission, reference, target))
            except Exception as error:
                records.append(invalid_case(reference, "runner failure: " + str(error)[:300]))
        report = aggregate(records, target)
        report["timing_kind"] = "trusted sandbox wall time including startup and I/O"
    except Exception as error:
        report = {"verification_mode": "A_BASELINE_IMPROVEMENT", "valid": False, "status": "infrastructure_failure", "core_score": 0.0, "worst_family": None, "worst_family_score": 0.0, "runtime_score": 0.0, "passed": False, "reason": "evaluation infrastructure failure: " + str(error)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, allow_nan=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

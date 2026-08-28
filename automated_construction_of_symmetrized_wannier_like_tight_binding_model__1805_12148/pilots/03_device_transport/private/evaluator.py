"""Author-side scoring with isolated submitted execution and explicit trusted controls."""

import argparse
import importlib.util
import json
import os
import resource
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
import psutil

PRIVATE = Path(__file__).resolve().parent
WEIGHTS = {"sigma": 0.25, "mode_counts": 0.10, "transmission": 0.20,
           "channels": 0.20, "partition_noise": 0.15, "lb_conductance": 0.10}
FLOORS = {"sigma": 0.05, "mode_counts": 1.0, "transmission": 0.01,
          "channels": 0.001, "partition_noise": 0.005, "lb_conductance": 0.01}
BASELINE_ERROR_FLOOR = 1e-8
SCORING_VERSION = "post_audit_nonsaturating_v1"


def numerical_errors(prediction, reference):
    groups = {name: [] for name in WEIGHTS}
    details = {}
    for key, expected in reference.items():
        group = "sigma" if key.startswith("sigma_") else key
        status = "ok"
        actual = prediction.get(key)
        if actual is None:
            error, status = 1.0, "missing"
        elif actual.shape != expected.shape:
            error, status = 1.0, "wrong_shape"
        elif actual.dtype.kind not in "fciu" or not np.all(np.isfinite(actual)):
            error, status = 1.0, "nonfinite_or_nonnumeric"
        elif group != "sigma" and np.iscomplexobj(actual) and np.max(np.abs(actual.imag)) > 1e-10:
            error, status = 1.0, "unexpected_complex_values"
        else:
            denominator = np.linalg.norm(expected.ravel()) + FLOORS[group] * np.sqrt(expected.size)
            error = float(np.linalg.norm((actual - expected).ravel()) / denominator)
        details[key] = {"error": error, "status": status}
        groups[group].append(error)
    errors = {group: float(np.mean(values)) for group, values in groups.items()}
    return errors, details


def score_components(errors, details, baseline):
    scores = {}
    for group in WEIGHTS:
        baseline_error = float(baseline[group])
        if not np.isfinite(baseline_error) or baseline_error < 0:
            raise ValueError("Baseline errors must be finite and nonnegative")
        valid = all(detail["status"] == "ok" for key, detail in details.items()
                    if ("sigma" if key.startswith("sigma_") else key) == group)
        scores[group] = (1.0 / (1.0 + 9.0 * errors[group] / max(baseline_error, BASELINE_ERROR_FLOOR))
                         if valid else 0.0)
    return scores


def limits(timeout_seconds, memory_mb):
    def apply_limits():
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 ** 2, memory_mb * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CPU, (timeout_seconds, timeout_seconds + 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2, 128 * 1024 ** 2))
    return apply_limits


def run_submission(submission, input_path, output_path, timeout_seconds, memory_mb, trusted_reference=False):
    if not trusted_reference:
        helper_path = PRIVATE.parents[2] / "authoring/sandbox_exec.py"
        sys.dont_write_bytecode = True
        specification = importlib.util.spec_from_file_location("pilot03_sandbox_exec", helper_path)
        helper = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(helper)
        measured = helper.run_submission(
            submission / "solve.py", input_path, output_path, PRIVATE.parent / "participant",
            timeout=timeout_seconds, memory_gib=memory_mb // 1024
        )
        return {"runtime_seconds": measured["seconds"],
                "peak_rss_mb": (measured["peak_rss_kib"] or 0) / 1024,
                "returncode": measured["returncode"], "timed_out": measured["returncode"] == 124,
                "log_tail": measured["log_tail"], "sandbox": "bwrap via parent sandbox_exec.py"}
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["OPENBLAS_NUM_THREADS"] = "1"
    environment["OMP_NUM_THREADS"] = "1"
    environment["MKL_NUM_THREADS"] = "1"
    log_path = output_path.with_suffix(".log")
    started = time.perf_counter()
    peak_rss = 0
    timed_out = False
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            [sys.executable, str(submission / "solve.py"), "--input", str(input_path), "--output", str(output_path)],
            cwd=submission, env=environment, stdout=log_file, stderr=subprocess.STDOUT,
            start_new_session=True, preexec_fn=limits(timeout_seconds, memory_mb)
        )
        while process.poll() is None:
            try:
                observed = psutil.Process(process.pid)
                memory = observed.memory_info().rss
                memory += sum(child.memory_info().rss for child in observed.children(recursive=True))
                peak_rss = max(peak_rss, memory)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            if time.perf_counter() - started > timeout_seconds:
                os.killpg(process.pid, signal.SIGKILL)
                timed_out = True
                break
            time.sleep(0.03)
        process.wait()
    return {"runtime_seconds": time.perf_counter() - started, "peak_rss_mb": peak_rss / 1024 ** 2,
            "returncode": process.returncode, "timed_out": timed_out,
            "log_tail": log_path.read_text(errors="replace")[-2400:]}


def evaluate(submission, split, output, calibrate_baseline=False, trusted_reference=False):
    if trusted_reference and not submission.is_relative_to(PRIVATE / "reference"):
        raise ValueError("Trusted execution is restricted to author-only reference entrypoints")
    directory = PRIVATE / "challenge_pool" / split
    manifest = json.loads((directory / "manifest.json").read_text())
    if len(manifest) != 4:
        raise ValueError("Incomplete private split; finish reference generation first")
    baseline_path = PRIVATE / "reference/baseline_errors.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())["errors"]
    else:
        baseline = {family: {group: 1.0 for group in WEIGHTS} for family in {case["family"] for case in manifest}}
    run_directory = PRIVATE / "runs" / uuid.uuid4().hex
    run_directory.mkdir(parents=True)
    per_case = []
    for case in manifest:
        output_path = run_directory / case["id"] / "result.npz"
        output_path.parent.mkdir()
        execution = run_submission(submission, directory / case["input"], output_path,
                                   case["timeout_seconds"], case["memory_mb"], trusted_reference)
        with np.load(directory / case["reference"], allow_pickle=False) as archive:
            reference = {key: archive[key] for key in archive.files}
        prediction = {}
        if execution["returncode"] == 0 and not execution["timed_out"] and output_path.exists():
            try:
                with np.load(output_path, allow_pickle=False) as archive:
                    prediction = {key: archive[key] for key in reference if key in archive}
            except (ValueError, OSError, EOFError) as error:
                execution["output_error"] = str(error)
        errors, details = numerical_errors(prediction, reference)
        component_scores = score_components(errors, details, baseline[case["family"]])
        score = sum(WEIGHTS[group] * component_scores[group] for group in WEIGHTS)
        row = {"id": case["id"], "family": case["family"], "score": score,
               "errors": errors, "field_errors": details, "component_scores": component_scores, **execution}
        per_case.append(row)
        print(json.dumps({key: row[key] for key in ("id", "family", "score", "runtime_seconds", "peak_rss_mb")}), flush=True)
    families = sorted({case["family"] for case in manifest})
    family_scores = {family: float(np.mean([case["score"] for case in per_case if case["family"] == family]))
                     for family in families}
    report = {"core_score": float(np.mean(list(family_scores.values()))),
              "worst_family_score": min(family_scores.values()), "family_scores": family_scores,
              "per_case": per_case, "split": split, "submission": str(submission),
              "scoring": "Weighted nonsaturating baseline-relative score: 1/(1+9*error/max(baseline_error,scientific_floor)); invalid groups score zero.",
              "scoring_version": SCORING_VERSION, "baseline_error_floor": BASELINE_ERROR_FLOOR,
              "baseline_errors": baseline, "baseline_source": str(baseline_path),
              "weights": WEIGHTS, "normalization_floors": FLOORS,
              "execution_isolation": "author-only trusted control" if trusted_reference else "parent bwrap helper; private trees are not mounted"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    if calibrate_baseline:
        if split != "test":
            raise ValueError("Calibrate only on test; preserve confirmation cases")
        calibration = {family: {group: float(np.mean([case["errors"][group] for case in per_case if case["family"] == family]))
                                for group in WEIGHTS} for family in families}
        baseline_path.write_text(json.dumps({"errors": calibration, "report": str(output),
                                            "baseline": "Unextended historical bulk Fourier capability, no transport outputs."}, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--split", choices=["test", "challenge", "confirmation"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibrate-baseline", action="store_true")
    parser.add_argument("--trusted-reference", action="store_true")
    arguments = parser.parse_args()
    evaluate(arguments.submission.resolve(), arguments.split, arguments.output.resolve(), arguments.calibrate_baseline, arguments.trusted_reference)

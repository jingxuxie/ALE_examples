import argparse
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parent
COMPONENTS = ("mean", "variance", "correlation", "replica_mean", "replica_covariance")
FLOORS = {"mean": 0.02, "variance": 0.10, "correlation": 0.02,
          "replica_mean": 0.02, "replica_covariance": 0.10}
TIMEOUT = 120


class SubmissionFailure(ValueError):
    def __init__(self, message, times):
        super().__init__(message)
        self.times = times


def numeric_statistics(value, dimension):
    if not isinstance(value, dict):
        raise ValueError("statistics must be an object")
    if (np.asarray(value.get("mean")).dtype.kind not in "fi"
            or np.asarray(value.get("covariance")).dtype.kind not in "fi"):
        raise ValueError("statistics must contain JSON numbers, not strings or booleans")
    mean = np.asarray(value.get("mean"), dtype=float)
    covariance = np.asarray(value.get("covariance"), dtype=float)
    if mean.shape != (dimension,) or covariance.shape != (dimension, dimension):
        raise ValueError("wrong mean or covariance shape")
    if not np.isfinite(mean).all() or not np.isfinite(covariance).all():
        raise ValueError("nonfinite statistics")
    scale = max(float(np.max(np.abs(covariance))), 1e-16)
    if np.max(np.abs(covariance - covariance.T)) > 1e-7 * scale + 1e-15:
        raise ValueError("covariance is not symmetric")
    if np.linalg.eigvalsh((covariance + covariance.T) / 2).min() < -1e-7 * scale - 1e-15:
        raise ValueError("covariance is not positive semidefinite")
    if np.any(np.diag(covariance) <= 0):
        raise ValueError("covariance diagonal must be positive for these nonconstant observables")
    return mean, (covariance + covariance.T) / 2


def compare_statistics(actual, expected, dimension):
    mean, covariance = numeric_statistics(actual, dimension)
    target_mean, target_covariance = numeric_statistics(expected, dimension)
    target_deviation = np.sqrt(np.diag(target_covariance))
    deviation = np.sqrt(np.diag(covariance))
    target_correlation = target_covariance / np.outer(target_deviation, target_deviation)
    correlation = covariance / np.outer(deviation, deviation)
    eigenvalues, eigenvectors = np.linalg.eigh(target_correlation)
    inverse_root = (eigenvectors / np.sqrt(np.maximum(eigenvalues, 1e-6))) @ eigenvectors.T
    standardized_mean = (mean - target_mean) / target_deviation
    mean_error = float(np.linalg.norm(inverse_root @ standardized_mean) / math.sqrt(dimension))
    variance_error = float(np.sqrt(np.mean(np.log(np.diag(covariance)
                                                  / np.diag(target_covariance)) ** 2)))
    off_diagonal = ~np.eye(dimension, dtype=bool)
    correlation_error = float(np.sqrt(np.mean((correlation - target_correlation)[off_diagonal] ** 2)))
    standardized_covariance = covariance / np.outer(target_deviation, target_deviation)
    joint_error = float(np.linalg.norm(inverse_root @ (standardized_covariance - target_correlation)
                                       @ inverse_root, ord="fro") / math.sqrt(dimension))
    errors = {"mean": mean_error, "variance": variance_error,
              "correlation": correlation_error, "joint": joint_error}
    if not all(math.isfinite(error) for error in errors.values()):
        raise ValueError("statistics comparison overflow")
    return errors


def measure_errors(actual, expected):
    if not isinstance(actual, dict) or actual.get("schema_version") != 1:
        raise ValueError("unsupported output schema")
    if not isinstance(actual.get("analyses"), list) or len(actual["analyses"]) != len(expected["analyses"]):
        raise ValueError("missing or extra analyses")
    results = []
    for actual_block, expected_block in zip(actual["analyses"], expected["analyses"]):
        if actual_block.get("block_size") != expected_block["block_size"]:
            raise ValueError("wrong blocking scale or order")
        dimension = len(expected_block["pooled"]["mean"])
        pooled = compare_statistics(actual_block.get("pooled"), expected_block["pooled"], dimension)
        replicas = actual_block.get("replicas")
        if not isinstance(replicas, list) or len(replicas) != len(expected_block["replicas"]):
            raise ValueError("wrong replica count")
        replica_errors = [compare_statistics(actual_replica, target_replica, dimension)
                          for actual_replica, target_replica in zip(replicas, expected_block["replicas"])]
        results.append({"mean": pooled["mean"], "variance": pooled["variance"],
                        "correlation": pooled["correlation"],
                        "replica_mean": max(error["mean"] for error in replica_errors),
                        "replica_covariance": max(error["joint"] for error in replica_errors)})
    return results


def score_answer(actual, expected, weak_errors):
    errors = measure_errors(actual, expected)
    blocks = []
    for expected_block, block_errors, weak_block in zip(expected["analyses"], errors, weak_errors):
        scales = {name: max(weak_block[name], FLOORS[name]) for name in COMPONENTS}
        scores = {name: 1.0 / (1.0 + 3.0 * block_errors[name] / scales[name]) for name in COMPONENTS}
        geometric = math.exp(sum(math.log(max(scores[name], 1e-300)) for name in COMPONENTS)
                             / len(COMPONENTS))
        score = min(geometric, scores["variance"], scores["correlation"], scores["replica_covariance"])
        blocks.append({"block_size": expected_block["block_size"], "score": score,
                       "components": scores, "component_errors": block_errors, "scales": scales})
    return {"score": min(block["score"] for block in blocks),
            "components": {name: min(block["components"][name] for block in blocks) for name in COMPONENTS},
            "component_errors": {name: max(block["component_errors"][name] for block in blocks)
                                 for name in COMPONENTS},
            "blocks": blocks}


def stage_submission(submission, destination):
    source = Path(submission).absolute()
    if source.is_symlink():
        raise ValueError("submission symlinks are not accepted")
    if source.is_file():
        destination.mkdir()
        shutil.copyfile(source, destination / "solve.py")
    elif source.is_dir():
        if not (source / "solve.py").is_file():
            raise ValueError("submission directory has no solve.py")
        for entry in source.rglob("*"):
            if entry.is_symlink():
                raise ValueError("submission contains a symlink")
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    else:
        raise ValueError("submission path does not exist")


def process_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT + 1))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2, 16 * 1024 ** 2))


def run_submission(submission, input_path):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="signed_stats_") as temporary:
        directory = Path(temporary)
        staged = directory / "submission"
        stage_submission(submission, staged)
        staged_input = directory / "input.json"
        staged_output = directory / "output.json"
        shutil.copyfile(input_path, staged_input)
        environment = {"PATH": os.pathsep.join((str(Path(sys.executable).parent), "/usr/bin", "/bin")),
                       "HOME": str(directory), "TMPDIR": str(directory), "LANG": "C.UTF-8",
                       "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        command = [sys.executable, str(staged / "solve.py"), "--input", str(staged_input),
                   "--output", str(staged_output)]
        wrapper = os.environ.get("ALPS_EVAL_WRAPPER")
        if wrapper:
            command = [sys.executable, str(Path(wrapper).resolve()), "--participant",
                       str(ROOT.parent / "participant"), "--submission", str(Path(submission).resolve()),
                       "--work", str(directory), "--timeout", str(TIMEOUT),
                       "--memory-mb", "2048", "--"] + command
        timed_out = False
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, cwd=staged, env=environment, stdout=stdout, stderr=stderr,
                                       preexec_fn=None if wrapper else process_limits, start_new_session=True)
            try:
                process.wait(timeout=TIMEOUT + 10 if wrapper else TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                timed_out = True
        times = {"wall_sec": time.monotonic() - started}
        resource_path = directory / "_resource.json"
        if resource_path.is_file():
            try:
                resources = json.loads(resource_path.read_text())
                times.update(resources)
            except (OSError, ValueError, TypeError):
                times["resource_report_error"] = "malformed _resource.json"
        if timed_out:
            raise SubmissionFailure("submission exceeded 120-second wall limit", times)
        if process.returncode:
            message = (directory / "stderr.log").read_bytes()[-2000:].decode("utf-8", errors="replace")
            raise SubmissionFailure("submission exited %s: %s" % (process.returncode, message), times)
        if not staged_output.is_file():
            raise SubmissionFailure("submission did not write the requested output", times)
        if staged_output.is_symlink() or staged_output.stat().st_size > 2 * 1024 ** 2:
            raise SubmissionFailure("output is a symlink or exceeds 2 MiB", times)
        try:
            answer = json.loads(staged_output.read_text())
        except (OSError, ValueError) as error:
            raise SubmissionFailure("invalid output JSON: " + str(error), times)
    return answer, times


def evaluate(submission, split):
    started = time.monotonic()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    records = []
    for entry in manifest[split]:
        case_started = time.monotonic()
        record = {"case_id": entry["case_id"], "family": entry["family"], "errors": []}
        try:
            answer, times = run_submission(submission, ROOT / entry["input"])
            expected = json.loads((ROOT / entry["reference"]).read_text())
            record.update(score_answer(answer, expected, entry["weak_errors"]))
            record["times"] = times
        except Exception as error:
            record.update({"score": 0.0, "components": {name: 0.0 for name in COMPONENTS},
                           "component_errors": {name: None for name in COMPONENTS}, "blocks": [],
                           "times": getattr(error, "times", {"wall_sec": time.monotonic() - case_started}),
                           "errors": [type(error).__name__ + ": " + str(error)]})
        records.append(record)
    families = {}
    for name in sorted({record["family"] for record in records}):
        family_cases = [record for record in records if record["family"] == name]
        families[name] = {"score": float(np.mean([record["score"] for record in family_cases])),
                          "case_count": len(family_cases),
                          "components": {component: float(np.mean([record["components"][component]
                                                                    for record in family_cases]))
                                         for component in COMPONENTS}}
    average = float(np.mean([record["score"] for record in records]))
    return {"split": split, "mean_core_score": average, "mean_score": average,
            "worst_family_score": min(family["score"] for family in families.values()),
            "families": families, "cases": records,
            "times": {"total_wall_sec": time.monotonic() - started},
            "errors": [record["case_id"] for record in records if record["errors"]],
            "scoring": "1/(1+3*error/max(weak_error,floor)); exact strong=1; weak typically=0.25; covariance and hardest-scale caps"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--split", choices=("core", "challenge"), required=True)
    parser.add_argument("--report", required=True)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.split)
    report_path = Path(arguments.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"split": report["split"], "mean_core_score": report["mean_core_score"],
                      "worst_family_score": report["worst_family_score"], "failed_cases": len(report["errors"])}))


if __name__ == "__main__":
    main()

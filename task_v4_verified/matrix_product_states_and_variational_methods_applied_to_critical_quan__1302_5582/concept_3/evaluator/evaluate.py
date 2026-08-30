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

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("odd_gap", "even_gap", "odd_spacing")


class InvalidSubmission(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSubmission("Duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(value):
    raise InvalidSubmission("Nonstandard JSON numeric constant")


def load_json(path, maximum=64 * 1024 ** 2):
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise InvalidSubmission("JSON output must be a regular non-linked file")
    if metadata.st_size > maximum:
        raise InvalidSubmission("JSON exceeds size limit")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                          parse_constant=invalid_constant)
    except (UnicodeError, ValueError, RecursionError, OverflowError) as error:
        raise InvalidSubmission("Invalid strict JSON: " + type(error).__name__) from error


def verify_integrity(root=ROOT):
    manifest = load_json(root / "evaluator/hidden/integrity.json")
    for relative, expected in manifest["sha256"].items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("Trusted asset missing or linked: " + relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Trusted asset digest mismatch: " + relative)


def parse_predictions(payload, ids):
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "predictions"}:
        raise InvalidSubmission("Wrong top-level fields")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise InvalidSubmission("Wrong schema version")
    predictions = payload["predictions"]
    if not isinstance(predictions, list) or len(predictions) != len(ids):
        raise InvalidSubmission("Expected exactly one prediction per input")
    by_id = {}
    expected_ids = set(ids)
    for prediction in predictions:
        if not isinstance(prediction, dict) or set(prediction) != {"id", "targets"}:
            raise InvalidSubmission("Wrong prediction fields")
        identifier = prediction["id"]
        if not isinstance(identifier, str) or identifier not in expected_ids or identifier in by_id:
            raise InvalidSubmission("Unknown or duplicate case ID")
        targets = prediction["targets"]
        if not isinstance(targets, dict) or set(targets) != set(TARGETS):
            raise InvalidSubmission("Wrong target fields")
        values = []
        for target in TARGETS:
            value = targets[target]
            if type(value) not in (int, float):
                raise InvalidSubmission("Gaps must be JSON numbers, not booleans or strings")
            try:
                value = float(value)
            except (ValueError, OverflowError) as error:
                raise InvalidSubmission("Unrepresentable numeric gap") from error
            if not math.isfinite(value) or value <= 0:
                raise InvalidSubmission("Gaps must be finite and strictly positive")
            values.append(value)
        by_id[identifier] = values
    return np.array([by_id[identifier] for identifier in ids])


def metric_values(errors, families):
    family_means = {family: float(np.mean(errors[np.array(families) == family]))
                    for family in sorted(set(families))}
    mean_error = float(np.mean(errors))
    worst_error = max(family_means.values())
    core = math.exp(-mean_error / 0.05)
    worst = math.exp(-worst_error / 0.05)
    return {"score": 0.75 * core + 0.25 * worst, "core_score": core,
            "worst_family_score": worst, "mean_log_error": mean_error,
            "worst_family_mean_log_error": worst_error,
            "p95_log_error": float(np.quantile(errors, 0.95)),
            "family_mean_log_error": family_means}


def score_predictions(predicted, reference, families, bootstrap=1000):
    differences = np.log(predicted) - np.log(reference)
    errors = np.abs(differences)
    result = metric_values(errors, families)
    relative = np.abs(np.expm1(np.clip(differences, -745.0, math.log(1e100))))
    result.update({"median_relative_error": float(np.median(relative)),
                   "p95_relative_error": float(np.quantile(relative, 0.95)),
                   "mean_relative_error_capped": float(np.mean(relative)),
                   "relative_error_cap": 1e100,
                   "log_rmse": float(np.sqrt(np.mean(errors ** 2))),
                   "target_mean_log_error": dict(zip(TARGETS, np.mean(errors, axis=0).tolist())),
                   "case_count": len(families), "target_count": len(TARGETS),
                   "family_counts": {family: families.count(family) for family in sorted(set(families))}})
    result["primary_success"] = (result["mean_log_error"] <= 0.03
                                 and result["worst_family_mean_log_error"] <= 0.06
                                 and result["p95_log_error"] <= 0.12)
    if bootstrap:
        generator = np.random.default_rng(821703)
        groups = [np.flatnonzero(np.array(families) == family) for family in sorted(set(families))]
        scores = []
        means = []
        for repetition in range(bootstrap):
            indices = np.concatenate([generator.choice(group, size=len(group), replace=True) for group in groups])
            sample = metric_values(errors[indices], [families[index] for index in indices])
            scores.append(sample["score"])
            means.append(sample["mean_log_error"])
        result["bootstrap_95_percent"] = {
            "score": np.quantile(scores, [0.025, 0.975]).tolist(),
            "mean_log_error": np.quantile(means, [0.025, 0.975]).tolist(),
            "method": "1000 stratified case resamples; three targets kept together; descriptive only"
        }
    return result


def stage_submission(source, destination, maximum):
    source = source.absolute()
    if source.is_symlink() or not source.is_dir():
        raise InvalidSubmission("Submission must be a non-linked directory")
    destination.mkdir()
    total = 0
    count = 0
    for current, directories, files in os.walk(source, followlinks=False):
        current = Path(current)
        for name in directories + files:
            path = current / name
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise InvalidSubmission("Submission symlinks are forbidden")
            if not (stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode)):
                raise InvalidSubmission("Submission special files are forbidden")
            count += 1
            if count > 4096:
                raise InvalidSubmission("Too many submission files")
        for name in directories:
            (destination / (current / name).relative_to(source)).mkdir()
        for name in files:
            path = current / name
            total += path.stat().st_size
            if total > maximum:
                raise InvalidSubmission("Submission exceeds byte limit")
            shutil.copyfile(path, destination / path.relative_to(source))
    if not (destination / "predict.py").is_file():
        raise InvalidSubmission("Submission needs predict.py")


def sandbox_command(stage):
    executable = shutil.which("bwrap")
    if not executable:
        raise RuntimeError("bubblewrap is required; refusing an unsandboxed run")
    command = [executable, "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL",
               "--clearenv", "--ro-bind", "/usr", "/usr"]
    for directory in ("/bin", "/lib", "/lib64", "/sbin"):
        if Path(directory).is_symlink():
            command += ["--symlink", os.readlink(directory), directory]
        elif Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    for filename in ("/etc/ld.so.cache", "/etc/localtime", "/etc/alternatives"):
        if Path(filename).exists():
            command += ["--ro-bind", filename, filename]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--ro-bind", str(stage / "submission"), "/submission",
                "--ro-bind", str(stage / "public"), "/public",
                "--ro-bind", str(stage / "input.json"), "/input.json",
                "--ro-bind", str(stage / "limits.json"), "/limits.json",
                "--bind", str(stage / "output"), "/output", "--chdir", "/submission"]
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                   "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
                   "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                   "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"}
    for name, value in environment.items():
        command += ["--setenv", name, value]
    bootstrap = (ROOT / "evaluator/runner.py").read_text()
    command += ["--", "/usr/bin/python3", "-I", "-B", "-c", bootstrap]
    return command


def run_submission(submission, inputs, limits):
    runs = ROOT / "evaluator/hidden/.runs"
    runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run-", dir=runs) as temporary:
        stage = Path(temporary)
        stage_submission(submission, stage / "submission", limits["submission_mib"] * 1024 ** 2)
        shutil.copytree(ROOT / "participant/input", stage / "public")
        (stage / "input.json").write_text(json.dumps(inputs, allow_nan=False))
        (stage / "limits.json").write_text(json.dumps(limits, allow_nan=False))
        (stage / "output").mkdir()
        started = time.monotonic()
        with (stage / "stderr.log").open("wb") as error_stream:
            process = subprocess.Popen(sandbox_command(stage), stdout=subprocess.DEVNULL, stderr=error_stream,
                                       stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True,
                                       env={"PATH": "/usr/bin:/bin"})
            try:
                returncode = process.wait(timeout=limits["wall_seconds"])
            except subprocess.TimeoutExpired as error:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise InvalidSubmission("Wall timeout") from error
        elapsed = time.monotonic() - started
        if returncode != 0:
            detail = (stage / "stderr.log").read_bytes()[:2000].decode("utf-8", errors="replace")
            if "bwrap:" in detail or "seccomp" in detail:
                raise RuntimeError("Isolation setup failed; no unsafe fallback. " + detail[-400:])
            raise InvalidSubmission("Predictor exited nonzero (%d); resource violation or execution failure: %s"
                                    % (returncode, detail[-1000:]))
        output = stage / "output/predictions.json"
        if not output.exists() and not output.is_symlink():
            raise InvalidSubmission("Predictor did not create predictions.json")
        return load_json(output, limits["output_bytes"]), elapsed


def evaluate(submission, split="hidden"):
    verify_integrity()
    contract = load_json(ROOT / "evaluator/hidden/target_contract.json")
    if split == "hidden":
        inputs_path = ROOT / "evaluator/hidden/test_inputs.json"
        labels_path = ROOT / "evaluator/hidden/test_labels.json"
    else:
        inputs_path = ROOT / "participant/input/validation_inputs.json"
        labels_path = ROOT / "participant/input/validation_labels.json"
    inputs = load_json(inputs_path)
    ids = [case["id"] for case in inputs["cases"]]
    families = [case["family"] for case in inputs["cases"]]
    payload, elapsed = run_submission(submission, inputs, contract["resources"])
    predicted = parse_predictions(payload, ids)
    verify_integrity()
    reference = parse_predictions(load_json(labels_path), ids)
    result = score_predictions(predicted, reference, families)
    result.update({"status": "ok", "split": split, "predictor_wall_seconds": elapsed,
                   "target_version": contract["version"],
                   "isolation": "bubblewrap namespaces/read-only mounts + seccomp + rlimits"})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("hidden", "validation"), default="hidden")
    arguments = parser.parse_args()
    try:
        result = evaluate(arguments.submission, arguments.split)
        exitcode = 0
    except InvalidSubmission as error:
        result = {"status": "invalid_submission", "score": 0.0, "primary_success": False, "error": str(error)}
        exitcode = 1
    except Exception as error:
        result = {"status": "evaluator_error", "score": 0.0, "primary_success": False,
                  "error": type(error).__name__ + ": " + str(error)}
        exitcode = 2
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "score", "primary_success")}, allow_nan=False))
    raise SystemExit(exitcode)


if __name__ == "__main__":
    main()

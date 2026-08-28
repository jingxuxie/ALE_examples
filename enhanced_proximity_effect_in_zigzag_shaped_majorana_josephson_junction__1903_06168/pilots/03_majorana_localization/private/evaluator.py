import argparse
import copy
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

PILOT = Path(__file__).resolve().parents[1]
PRIVATE = PILOT / "private"
REFERENCE = PRIVATE / "reference"
POOL = PRIVATE / "challenge_pool"
FAMILIES = ("bulk_tail", "finite_end")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_predictions(path):
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("output exceeds 8 MiB")
    payload = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    predictions = payload.get("predictions")
    if not isinstance(predictions, dict):
        raise ValueError("predictions must be an object")
    return predictions


def cases_for(split):
    all_cases = json.loads((POOL / "manifest.json").read_text())["cases"]
    public_ids = {case["id"] for case in json.loads((PILOT / "participant/input/manifest.json").read_text())["cases"]}
    return [case for case in all_cases if (case["id"] in public_ids) == (split == "public")]


def stage_inputs(destination, cases):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("input staging directory must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    for case in cases:
        shutil.copy2(POOL / case["file"], destination / case["file"])
    write_json(destination / "manifest.json", {"schema_version": 1, "cases": cases})


def length_quality(value, target, scale):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return 0.0
    try:
        value = float(value)
    except (OverflowError, ValueError):
        return 0.0
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return math.exp(-abs(math.log(value) - math.log(target)) / scale)


def profile_quality(value, target):
    try:
        if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
            return 0.0
        profile = np.asarray(value, dtype=float)
        expected = np.asarray(target, dtype=float)
        if profile.shape != expected.shape or not np.isfinite(profile).all() or (profile < 0).any():
            return 0.0
        if abs(float(profile.sum()) - 1) > 1e-5:
            return 0.0
        distance = 0.5 * np.sum((np.sqrt(profile) - np.sqrt(expected)) ** 2)
        return float(np.exp(-distance / 0.05))
    except (TypeError, ValueError, OverflowError):
        return 0.0


def raw_scores(predictions, cases, targets):
    rows = []
    for case in cases:
        case_id = case["id"]
        predicted = predictions.get(case_id, {})
        if not isinstance(predicted, dict):
            predicted = {}
        target = targets[case_id]
        row = {"id": case_id, "family": case["family"]}
        if case["family"] == "bulk_tail":
            row["length_quality"] = length_quality(predicted.get("xi_amplitude_nm"), target["xi_amplitude_nm"], 0.25)
            row["quality"] = row["length_quality"]
        else:
            row["profile_quality"] = profile_quality(predicted.get("rho_left"), target["rho_left"])
            row["length_quality"] = length_quality(predicted.get("xi_window_nm"), target["xi_window_nm"], 0.20)
            row["quality"] = (row["profile_quality"] + row["length_quality"]) / 2
        rows.append(row)
    quality = {family: float(np.mean([row["quality"] for row in rows if row["family"] == family])) for family in FAMILIES}
    return quality, rows


def score(predictions, cases, targets, calibration):
    raw, rows = raw_scores(predictions, cases, targets)
    families = {}
    for family in FAMILIES:
        weak = calibration["weak"][family]
        strong = calibration["strong"][family]
        if strong - weak < 0.05:
            raise ValueError(f"unusable calibration for {family}")
        normalized = float(np.clip((raw[family] - weak) / (strong - weak), 0, 1))
        families[family] = {"raw_quality": raw[family], "weak_anchor": weak,
                            "strong_anchor": strong, "score": normalized,
                            "case_count": sum(case["family"] == family for case in cases)}
    return {"score": float(np.mean([families[family]["score"] for family in FAMILIES])),
            "families": families, "cases": rows}


def resource_limits():
    resource.setrlimit(resource.RLIMIT_AS, (6 * 1024 ** 3, 6 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2, 16 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_submission(submission, cases, timeout):
    scratch = PRIVATE / "runs"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run_", dir=scratch) as temporary:
        run_root = Path(temporary)
        input_path, output_path = run_root / "input", run_root / "output.json"
        stage_inputs(input_path, cases)
        environment = dict(os.environ)
        environment.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
        environment.pop("PYTHONPATH", None)
        start = time.monotonic()
        with (run_root / "stdout.txt").open("wb") as stdout, (run_root / "stderr.txt").open("wb") as stderr:
            process = subprocess.Popen(
                [sys.executable, str(submission.resolve()), "--input", str(input_path), "--output", str(output_path)],
                cwd=run_root, env=environment, stdout=stdout, stderr=stderr,
                start_new_session=True, preexec_fn=resource_limits,
            )
            failure = None
            try:
                returncode = process.wait(timeout=timeout)
                if returncode:
                    failure = f"submission exited {returncode}"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                failure = f"timeout after {timeout} seconds"
        elapsed = time.monotonic() - start
        diagnostics = {"runtime_seconds": elapsed, "failure": failure,
                       "stderr_tail": (run_root / "stderr.txt").read_text(errors="replace")[-3000:]}
        if failure:
            return {}, diagnostics
        try:
            return read_predictions(output_path), diagnostics
        except (OSError, ValueError, TypeError) as error:
            diagnostics["failure"] = str(error)
            return {}, diagnostics


def load_calibration(split):
    return json.loads((REFERENCE / "calibration.json").read_text())[split]


def calibrate(timeout):
    targets = json.loads((REFERENCE / "targets.json").read_text())
    calibration, reports = {}, {}
    for split in ("holdout", "public"):
        cases = cases_for(split)
        calibration[split] = {}
        reports[split] = {}
        for name, script in (("weak", PILOT / "participant/workspace/finite_workflow.py"), ("strong", REFERENCE / "strong.py")):
            predictions, diagnostics = run_submission(script, cases, timeout)
            if diagnostics["failure"]:
                raise RuntimeError(diagnostics)
            quality, rows = raw_scores(predictions, cases, targets)
            calibration[split][name] = quality
            reports[split][name] = {"raw_quality": quality, "diagnostics": diagnostics, "cases": rows}
            write_json(REFERENCE / f"{name}_{split}_predictions.json", {"schema_version": 1, "predictions": predictions})
        assert all(calibration[split]["strong"][family] > 0.9999 for family in FAMILIES)
        assert all(calibration[split]["strong"][family] - calibration[split]["weak"][family] > 0.05 for family in FAMILIES)
    write_json(REFERENCE / "calibration.json", calibration)
    write_json(REFERENCE / "calibration_runs.json", reports)
    return calibration


def sanity_checks():
    cases = cases_for("holdout")
    targets = json.loads((REFERENCE / "targets.json").read_text())
    calibration = load_calibration("holdout")
    weak = read_predictions(REFERENCE / "weak_holdout_predictions.json")
    strong = read_predictions(REFERENCE / "strong_holdout_predictions.json")
    checks = {"weak": score(weak, cases, targets, calibration),
              "strong": score(strong, cases, targets, calibration),
              "missing": score({}, cases, targets, calibration)}
    assert checks["weak"]["score"] < 1e-12
    assert checks["strong"]["score"] > 1 - 1e-12
    assert checks["missing"]["score"] == 0
    assert length_quality(10 ** 4000, 1.0, 0.25) == 0
    assert length_quality(True, 1.0, 0.25) == 0
    assert profile_quality(["1.0"], [1.0]) == 0
    for family in FAMILIES:
        hybrid = copy.deepcopy(weak)
        for case in cases:
            if case["family"] == family:
                hybrid[case["id"]] = strong[case["id"]]
        checks[f"only_{family}"] = score(hybrid, cases, targets, calibration)
        assert abs(checks[f"only_{family}"]["score"] - 0.5) < 1e-12
    half_lengths = copy.deepcopy(strong)
    for case in cases:
        field = "xi_amplitude_nm" if case["family"] == "bulk_tail" else "xi_window_nm"
        half_lengths[case["id"]][field] /= 2
    checks["density_amplitude_factor_two_error"] = score(half_lengths, cases, targets, calibration)
    assert checks["density_amplitude_factor_two_error"]["score"] < 0.6
    constant_bulk = copy.deepcopy(weak)
    for case in cases:
        if case["family"] == "bulk_tail":
            constant_bulk[case["id"]] = {"xi_amplitude_nm": 26653.783980556494}
    checks["memorized_nominal_bulk"] = score(constant_bulk, cases, targets, calibration)
    public_predictions = read_predictions(REFERENCE / "strong_public_predictions.json")
    public_templates = {
        case["family"]: public_predictions[case["id"]] for case in cases_for("public")
    }
    copied_templates = {case["id"]: public_templates[case["family"]] for case in cases}
    checks["public_template_reused"] = score(copied_templates, cases, targets, calibration)
    invalid = copy.deepcopy(strong)
    for case in cases:
        field = "xi_amplitude_nm" if case["family"] == "bulk_tail" else "xi_window_nm"
        invalid[case["id"]][field] = float("nan")
    checks["nonfinite_lengths"] = score(invalid, cases, targets, calibration)
    assert all(row["length_quality"] == 0 for row in checks["nonfinite_lengths"]["cases"])
    negative = copy.deepcopy(strong)
    for case in cases:
        if case["family"] == "finite_end":
            negative[case["id"]]["rho_left"] = [-1] * len(targets[case["id"]]["rho_left"])
    checks["negative_profiles"] = score(negative, cases, targets, calibration)
    for row in checks["negative_profiles"]["cases"]:
        if row["family"] == "finite_end":
            assert row["profile_quality"] == 0
    for shape_index in range(1, 4):
        first, second = targets.get(f"e{shape_index}0"), targets.get(f"e{shape_index}1")
        if first is not None and second is not None:
            assert np.max(np.abs(np.array(first["rho_left"]) - second["rho_left"])) < 1e-12
    write_json(REFERENCE / "sanity_checks.json", checks)
    return {name: result["score"] for name, result in checks.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, default=PILOT / "attempt/solve.py")
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--export-input", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--split", choices=("holdout", "public"), default="holdout")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.calibrate:
        result = {"calibration": calibrate(args.timeout), "sanity": sanity_checks()}
    elif args.self_test:
        result = {"sanity": sanity_checks()}
    else:
        cases = cases_for(args.split)
        if args.export_input:
            stage_inputs(args.export_input.resolve(), cases)
            print(json.dumps({"exported_cases": len(cases), "input": str(args.export_input.resolve())}))
            return
        targets = json.loads((REFERENCE / "targets.json").read_text())
        diagnostics = {}
        if args.predictions:
            try:
                predictions = read_predictions(args.predictions)
            except (OSError, ValueError, TypeError) as error:
                predictions, diagnostics = {}, {"failure": str(error)}
        else:
            predictions, diagnostics = run_submission(args.submission, cases, args.timeout)
        result = score(predictions, cases, targets, load_calibration(args.split))
        result.update(diagnostics)
    if args.report:
        write_json(args.report, result)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

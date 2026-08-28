"""Private scoring API and baseline/reference validation runner."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

PRIVATE = Path(__file__).resolve().parent
PILOT = PRIVATE.parent
TARGET = PILOT.parents[1]
sys.path.insert(0, str(PRIVATE / "reference"))

import numpy as np

from physics import error_metrics, load_npz, validate_output


def score_details(actual, reference, baseline, case, input_data):
    """Return finite numeric component scores, aggregate score, and raw errors."""
    actual_metrics = error_metrics(actual, reference, input_data)
    baseline_metrics = case.get("baseline_metrics")
    if baseline_metrics is None:
        baseline_metrics = error_metrics(baseline, reference, input_data)

    def component(error, calibration, floor=1e-10):
        scale = max(float(calibration), floor)
        ratio = float(error) / scale
        return float(1.0 / (1.0 + ratio))

    output = {}
    for order in (2, 3):
        name = f"fc{order}_relative_error"
        output[f"fc{order}"] = component(actual_metrics[name], baseline_metrics[name])
    for order in (2, 3):
        observed = reference[f"heldout_f{order}"]
        name = f"heldout_force{order}_rmse"
        if len(observed):
            output[f"heldout_force{order}"] = component(actual_metrics[name], baseline_metrics[name], floor=1e-12)
        else:
            output[f"heldout_force{order}"] = 1.0
    for kind in ("acoustic", "permutation", "spacegroup"):
        values = [component(actual_metrics[f"{kind}_fc{order}"], baseline_metrics[f"{kind}_fc{order}"]) for order in (2, 3)]
        output[kind] = float(np.mean(values))
    output["support"] = component(actual_metrics["support_fc3"], baseline_metrics["support_fc3"])
    for order in (2, 3):
        def branch_error(metrics):
            value = metrics[f"fc{order}_relative_error"]
            value += sum(metrics[f"{kind}_fc{order}"] for kind in ("acoustic", "permutation", "spacegroup"))
            force_order = 2 if order == 2 and len(reference["heldout_u2"]) else 3
            observed_scale = max(float(np.sqrt(np.mean(reference[f"heldout_f{force_order}"] ** 2))), 1e-12)
            value += metrics[f"heldout_force{force_order}_rmse"] / observed_scale
            if order == 3:
                value += metrics["support_fc3"]
            return value
        actual_branch = branch_error(actual_metrics)
        baseline_branch = branch_error(baseline_metrics)
        output[f"fc{order}_branch"] = component(actual_branch, baseline_branch)
        output[f"raw_fc{order}_branch_error"] = float(actual_branch)
        output[f"raw_fc{order}_baseline_branch_error"] = float(baseline_branch)
    output["score"] = float((output["fc2_branch"] + output["fc3_branch"]) / 2.0)
    output.update({"raw_" + key: float(value) for key, value in actual_metrics.items()})
    return output


def score_case(actual, reference, baseline, case, input_data):
    """Expose exactly two scored branches to the shared evaluator."""
    details = score_details(actual, reference, baseline, case, input_data)
    return {
        f"fc{order}": {
            "score": details[f"fc{order}_branch"],
            "error": details[f"raw_fc{order}_branch_error"],
            "baseline_error": details[f"raw_fc{order}_baseline_branch_error"],
            "tensor_relative_error": details[f"raw_fc{order}_relative_error"],
            "acoustic_residual": details[f"raw_acoustic_fc{order}"],
            "permutation_residual": details[f"raw_permutation_fc{order}"],
            "spacegroup_residual": details[f"raw_spacegroup_fc{order}"],
            "heldout_force2_rmse": details["raw_heldout_force2_rmse"],
            "heldout_force3_rmse": details["raw_heldout_force3_rmse"],
            "support_residual": details["raw_support_fc3"] if order == 3 else 0.0,
        }
        for order in (2, 3)
    }


def load_common_runner():
    path = TARGET / "author/evaluation.py"
    if not path.exists():
        raise RuntimeError("author/evaluation.py is not present; use --direct only for explicitly unisolated baseline validation")
    spec = importlib.util.spec_from_file_location("fitting_common_evaluation", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.sandbox_run


def direct_run(submission, input_path, output_dir, participant, timeout=180, memory_mb=8192):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "output.npz"
    timing_path = output_dir / "time.txt"
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.perf_counter()
    command = ["/usr/bin/time", "-f", "%e %M", "-o", str(timing_path), sys.executable, "-B", str(submission), str(input_path), str(output_path)]
    try:
        completed = subprocess.run(command, cwd=output_dir, env=environment, capture_output=True, text=True, timeout=timeout)
        status = "ok" if completed.returncode == 0 and output_path.exists() else "error"
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as error:
        status = "timeout"
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
    max_rss = None
    if timing_path.exists():
        for line in reversed(timing_path.read_text().splitlines()):
            fields = line.split()
            if len(fields) == 2:
                try:
                    max_rss = int(fields[1])
                    break
                except ValueError:
                    pass
    return {"status": status, "seconds": time.perf_counter() - start, "max_rss_kb": max_rss, "output_path": str(output_path), "stdout": stdout, "stderr": stderr, "isolation": "direct; memory limit not enforced"}


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=PILOT / "participant/workspace/solve.py")
    parser.add_argument("--split", choices=["pool", "initial", "heldout", "all"], default="all")
    parser.add_argument("--case", action="append")
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--calibrate-baseline", action="store_true")
    parser.add_argument("--validate-reference", action="store_true")
    parser.add_argument("--report", type=Path, default=PRIVATE / "reference/author_measurements/validation.json")
    args = parser.parse_args()
    manifest_path = PRIVATE / "challenge_pool/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    runner = direct_run if args.direct else load_common_runner()
    records = []
    for case in manifest:
        selected_split = "pool" if args.split == "initial" else args.split
        if selected_split != "all" and case["split"] != selected_split:
            continue
        if args.case and case["id"] not in args.case:
            continue
        input_data = load_npz(PRIVATE / case["input"])
        reference = load_npz(PRIVATE / case["reference"])
        start = time.perf_counter()
        run = runner(args.submission.resolve(), (PRIVATE / case["input"]).resolve(), (PRIVATE / "reference/author_measurements" / ("baseline" if args.calibrate_baseline else "submission") / case["id"]).resolve(), (PILOT / "participant").resolve(), timeout=case["timeout"], memory_mb=case["memory_mb"])
        run = {key: str(value) if isinstance(value, Path) else value for key, value in run.items()}
        record = {"id": case["id"], "family": case["family"], "split": case["split"], "run": run}
        try:
            if run["status"] not in ("ok", "success"):
                raise RuntimeError(f"solver execution failed: {run['status']}: {run.get('stderr', '')}")
            actual = load_npz(Path(run["output_path"]))
            validate_output(actual, input_data)
            if args.calibrate_baseline:
                shutil.copyfile(run["output_path"], PRIVATE / case["baseline"])
                case["baseline_metrics"] = error_metrics(actual, reference, input_data)
                case["baseline_run"] = {key: run.get(key) for key in ("status", "seconds", "max_rss_kb", "isolation")}
            baseline = load_npz(PRIVATE / case["baseline"])
            record["components"] = score_details(actual, reference, baseline, case, input_data)
            record["classification"] = "substantive numerical error" if record["components"]["score"] < 0.90 else "accurate"
            if args.validate_reference:
                record["reference_components"] = score_details(reference, reference, baseline, case, input_data)
                if record["reference_components"]["score"] <= 0.90:
                    raise ValueError(f"reference score does not exceed 0.90: {record['reference_components']['score']}")
            record["status"] = "ok"
        except Exception as error:
            record["status"] = "failed"
            record["error"] = f"{type(error).__name__}: {error}"
            record["classification"] = "clerical/execution/validation failure"
        record["evaluation_seconds"] = time.perf_counter() - start
        records.append(record)
        print(json.dumps({"id": case["id"], "status": record["status"], "score": record.get("components", {}).get("score"), "reference_score": record.get("reference_components", {}).get("score"), "seconds": run.get("seconds"), "max_rss_kb": run.get("max_rss_kb"), "error": record.get("error")}), flush=True)
    if args.calibrate_baseline:
        write_json(manifest_path, manifest)
        for case in manifest:
            write_json(PRIVATE / "challenge_pool" / case["id"] / "metadata.json", case)
    scores = [record["components"]["score"] for record in records if record["status"] == "ok"]
    references = [record["reference_components"]["score"] for record in records if record["status"] == "ok" and "reference_components" in record]
    report = {
        "records": records,
        "mean_score": float(np.mean(scores)) if scores else None,
        "minimum_reference_score": min(references) if references else None,
        "all_passed": bool(records) and all(record["status"] == "ok" for record in records),
        "solver": str(args.submission.resolve()), "mode": "direct" if args.direct else "common sandbox_run",
        "threads": {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    }
    write_json(args.report, report)
    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

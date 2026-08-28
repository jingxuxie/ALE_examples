import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np

from numerics import diagnostics, log_omega0


ROOT = Path(__file__).resolve().parents[1]
from isolated import run_submission


def read_result(path, count):
    if path.stat().st_size > 2_000_000:
        raise ValueError("output exceeds two megabytes")
    if path.read_bytes()[:2] == b"PK":
        with zipfile.ZipFile(path) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 2_000_000:
                raise ValueError("uncompressed output exceeds two megabytes")
        with np.load(path, allow_pickle=False) as archive:
            result = {name: np.asarray(archive[name], dtype=float) for name in archive.files}
    else:
        result = {name: np.asarray(value, dtype=float) for name, value in json.loads(path.read_text()).items()}
    expected = {"saddle": (count, 3), "barrier_meV": (), "eigenvalues_min_meV": (2 * count,), "eigenvalues_saddle_meV": (2 * count,), "log_omega0": ()}
    for name, shape in expected.items():
        if name not in result or result[name].shape != shape or not np.all(np.isfinite(result[name])):
            raise ValueError(f"invalid {name}: expected finite shape {shape}")
    if np.max(np.abs(np.linalg.norm(result["saddle"], axis=1) - 1)) > 1e-5:
        raise ValueError("spins must have unit norm within 1e-5")
    for name in ["eigenvalues_min_meV", "eigenvalues_saddle_meV"]:
        if np.any(np.diff(result[name]) < 0):
            raise ValueError("eigenvalues must be sorted ascending")
    return result


def component_losses(case, result, reference):
    minimum = diagnostics(case, np.asarray(case["minimum_a"]))
    saddle = diagnostics(case, np.asarray(result["saddle"]))
    expected_barrier = reference["barrier_meV"]
    actual_barrier = saddle["energy_meV"] - minimum["energy_meV"]
    reported_barrier = float(result["barrier_meV"])
    barrier = abs(reported_barrier - expected_barrier) / (0.03 * expected_barrier + 0.005)
    barrier += abs(reported_barrier - actual_barrier) / (0.02 * expected_barrier + 0.002)
    stationarity = math.asinh(saddle["residual_meV"] / 2e-5)
    spectrum_actual = saddle["eigenvalues"]
    inertia = float(np.logaddexp(0.0, spectrum_actual[0] / 0.02) + np.sum(np.logaddexp(0.0, -spectrum_actual[1:] / 0.02)))
    spectral_errors = []
    for name, actual in [("eigenvalues_min_meV", minimum["eigenvalues"]), ("eigenvalues_saddle_meV", saddle["eigenvalues"])]:
        predicted = np.asarray(result[name])
        difference = np.arcsinh(predicted / 0.001) - np.arcsinh(actual / 0.001)
        spectral_errors.append(float(np.sqrt(np.mean(difference**2))))
    spectrum = float(np.mean(spectral_errors) / 0.12)
    omega = abs(float(result["log_omega0"]) - reference["log_omega0"]) / 0.25
    loss = inertia + 0.25 * barrier + 0.30 * spectrum + 0.25 * omega + 0.20 * stationarity
    return float(loss), {
        "barrier_loss": barrier, "stationarity_loss": stationarity, "spectrum_loss": spectrum,
        "harmonic_prefactor_loss": omega, "inertia_loss": inertia,
        "residual_meV": saddle["residual_meV"], "negative_modes": saddle["negative_modes"],
        "zero_modes": saddle["zero_modes"], "recomputed_barrier_meV": actual_barrier,
    }


def weak_result(case):
    count = case["n_spins"]
    return {"saddle": np.array(case["minimum_a"]), "barrier_meV": 0.0,
            "eigenvalues_min_meV": np.ones(2 * count),
            "eigenvalues_saddle_meV": np.array([-1.0] + [1.0] * (2 * count - 1)), "log_omega0": 0.0}


def physical_loss(case, result, reference):
    _, checks = component_losses(case, result, reference)
    _, weak_checks = component_losses(case, weak_result(case), reference)
    search = checks["inertia_loss"] + 0.25 * checks["barrier_loss"] + 0.20 * checks["stationarity_loss"]
    fluctuation = 0.30 * checks["spectrum_loss"] + 0.25 * checks["harmonic_prefactor_loss"]
    weak_search = weak_checks["inertia_loss"] + 0.25 * weak_checks["barrier_loss"] + 0.20 * weak_checks["stationarity_loss"]
    weak_fluctuation = 0.30 * weak_checks["spectrum_loss"] + 0.25 * weak_checks["harmonic_prefactor_loss"]
    checks["relative_search_loss"] = search / weak_search
    checks["relative_fluctuation_loss"] = fluctuation / weak_fluctuation
    balanced = (0.5 * (checks["relative_search_loss"] ** 4 + checks["relative_fluctuation_loss"] ** 4)) ** 0.25
    return balanced, checks


def calibrated_score(loss, weak_loss, strong_loss, runtime, reference_runtime):
    runtime_loss = 0.001 * math.log1p(runtime / max(0.25, reference_runtime))
    gain = (weak_loss - loss - runtime_loss) / (weak_loss - strong_loss)
    score = -math.expm1(-math.log(2.0) * math.exp(math.log(4.0) * gain))
    return score, gain, runtime_loss


def copy_submission(submission, target):
    total = 0
    for source in submission.rglob("*"):
        if source.is_symlink():
            raise ValueError("submission symlinks are not permitted")
        relative = source.relative_to(submission)
        if any(part in {".git", "__pycache__", ".numba_cache"} for part in relative.parts):
            continue
        if source.is_file():
            total += source.stat().st_size
            if total > 32 * 1024**2:
                raise ValueError("submission exceeds 32 MiB")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    if not (target / "solve.py").is_file():
        raise ValueError("submission must contain solve.py")


def execute(submission, case, run_parent):
    with tempfile.TemporaryDirectory(prefix="case-", dir=run_parent) as temporary:
        directory = Path(temporary)
        safe_submission = directory / "submission"
        safe_submission.mkdir()
        copy_submission(submission, safe_submission)
        if not (safe_submission / "energy.py").exists():
            shutil.copyfile(ROOT / "participant" / "workspace" / "energy.py", safe_submission / "energy.py")
        case_path = directory / "case.json"
        case_path.write_text(json.dumps(case))
        output_path = directory / "output" / "output.npz"
        metrics = run_submission(safe_submission, case_path, output_path, ROOT / "participant", timeout=case["time_limit_seconds"], memory_gib=2.0)
        if metrics["timeout"] or metrics["returncode"] != 0:
            raise RuntimeError(f"isolated submission failed: {metrics}")
        result = read_result(output_path, case["n_spins"])
        return result, metrics["elapsed"], metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["initial", "challenge", "confirmation"], default="initial")
    args = parser.parse_args()
    submission = args.submission.resolve()
    directory = ROOT / "private" / ("reference" if args.split == "initial" else "challenge_pool") / args.split
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        parser.error(f"{args.split} is not frozen; confirmation needs fresh seeds generated privately")
    manifest = json.loads(manifest_path.read_text())
    for relative, digest in manifest["sha256"].items():
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"frozen reference hash mismatch: {relative}")
    cases = sorted(directory.glob("*/case.json"))
    run_parent = ROOT / "private" / "runs"
    run_parent.mkdir(exist_ok=True)
    records = []
    for case_path in cases:
        case = json.loads(case_path.read_text())
        reference = json.loads((case_path.parent / "solution.json").read_text())
        validation = json.loads((case_path.parent / "validation.json").read_text())
        strong_loss, strong_checks = physical_loss(case, reference, reference)
        weak_loss, _ = physical_loss(case, weak_result(case), reference)
        record = {"case_id": case["case_id"], "family": case["family"], "n_spins": case["n_spins"], "weak_anchor_loss": weak_loss, "strong_anchor_loss": strong_loss, "source_reference_seconds": validation["reference_runtime_seconds"]}
        if strong_checks["negative_modes"] != 1 or strong_checks["zero_modes"] or strong_loss >= weak_loss or strong_checks["residual_meV"] > 2e-6:
            raise RuntimeError(f"invalid independently checked native strong reference: {record}")
        try:
            result, runtime, isolation = execute(submission, case, run_parent)
            loss, checks = physical_loss(case, result, reference)
            score, gain, runtime_loss = calibrated_score(loss, weak_loss, strong_loss, runtime, validation["reference_runtime_seconds"])
            record.update({"score": score, "physical_loss": loss, "calibrated_gain": gain, "runtime_seconds": runtime, "runtime_loss": runtime_loss, "checks": checks, "isolation": isolation["isolation"], "peak_rss_kib": isolation.get("peak_rss_kib"), "status": "ok"})
        except Exception as error:
            record.update({"score": 0.0, "status": "failed", "error": str(error)})
        records.append(record)
        print(f"{case['case_id']}: {record['score']:.6f} {record['status']}", flush=True)
    families = {family: float(np.mean([record["score"] for record in records if record["family"] == family])) for family in sorted({record["family"] for record in records})}
    mean_family = float(np.mean(list(families.values())))
    worst_family = min(families.values())
    output = {"split": args.split, "score": 0.7 * mean_family + 0.3 * worst_family, "mean_family_score": mean_family, "worst_family_score": worst_family, "families": families, "cases": records, "reference_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "isolation_policy": "Private isolated.py: bubblewrap unshare-all, precise read-only submission/case/participant binds, writable output only; evaluator may require escalation outside nested sandbox."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

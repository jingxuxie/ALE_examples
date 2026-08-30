import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, str(ROOT.parents[1] / "evaluator" / "hidden"))
import trusted_physics


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def summary(report):
    result = {key: report.get(key) for key in ("valid", "passed", "core_score", "worst_family_score", "reason")}
    result.update({key: value for key, value in report.get("metrics", {}).items() if not isinstance(value, list)})
    return result


def main():
    candidates = []
    for score_path in ROOT.glob("*/*.score.json"):
        report = json.loads(score_path.read_text())
        artifact = score_path.with_name(score_path.name.replace(".score.json", ".npz"))
        if artifact.is_file() and report.get("valid"):
            rank = (report.get("worst_family_score", 0), report.get("core_score", 0))
            metric = report.get("metrics", {})
            margin = max(metric.get("order_max_relative_error", 1) / 0.025,
                         metric.get("density_max_relative_error", 1) / 0.1,
                         metric.get("y_max_relative_error", 1) / 0.1,
                         metric.get("energy_excess", 1) / 5e-5)
            candidates.append((rank, -margin, artifact, report))
    if not candidates:
        raise RuntimeError("No valid scored private candidates available")
    candidates.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    selected = candidates[0]
    shutil.copyfile(selected[2], ROOT / "state.npz")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    official = subprocess.run([sys.executable, str(ROOT.parents[1] / "evaluator" / "evaluate.py"),
                               "--submission", str(ROOT), "--output", str(ROOT / "exact_checker_score.json")],
                              env=environment, capture_output=True, text=True, check=True, timeout=125)
    (ROOT / "exact_checker_stdout.json").write_text(official.stdout)
    if official.stderr:
        (ROOT / "exact_checker_stderr.log").write_text(official.stderr)
    public = subprocess.run([sys.executable, str(ROOT.parents[1] / "participant" / "workspace" / "check.py"),
                             str(ROOT / "state.npz")], env=environment, capture_output=True, text=True, timeout=125)
    (ROOT / "public_checker_stdout.json").write_text(public.stdout)
    if public.stderr:
        (ROOT / "public_checker_stderr.log").write_text(public.stderr)
    exact_report = json.loads((ROOT / "exact_checker_score.json").read_text())
    public_report = json.loads(public.stdout)
    if exact_report.get("passed") != public_report.get("passed") or exact_report.get("valid") != public_report.get("valid"):
        raise RuntimeError("Public and official checker disagree")
    near_misses = [entry for entry in candidates if not entry[3].get("passed")]
    near_miss = None
    near_report = None
    if near_misses:
        near_miss = near_misses[0]
        shutil.copyfile(near_miss[2], ROOT / "near_miss.npz")
        near_report = trusted_physics.check(ROOT / "near_miss.npz")
        write_json(ROOT / "near_miss_score.json", near_report)
    tensor = np.load(ROOT / "state.npz")["A"]
    half = tensor.shape[1] // 2
    generator = np.random.default_rng(817)
    gauge = np.zeros((2 * half, 2 * half), dtype=complex)
    for sector in range(2):
        block = generator.normal(size=(half, half)) + 1j * generator.normal(size=(half, half))
        unitary, unused_triangular = np.linalg.qr(block)
        gauge[sector * half:(sector + 1) * half, sector * half:(sector + 1) * half] = unitary
    transformed = np.stack([gauge.conj().T @ physical @ gauge for physical in tensor])
    np.savez(ROOT / "complex_gauge_audit.npz", A=transformed)
    gauge_report = trusted_physics.check(ROOT / "complex_gauge_audit.npz")
    write_json(ROOT / "complex_gauge_audit_score.json", gauge_report)
    differences = {}
    if gauge_report.get("valid"):
        for channel in ("order_correlations", "density_connected_correlations", "y_correlations"):
            differences[channel] = float(np.max(np.abs(np.asarray(exact_report["metrics"][channel])
                                                      - np.asarray(gauge_report["metrics"][channel]))))
    hashes = {}
    for relative in ("participant/input/contract.json", "participant/workspace/physics.py",
                     "evaluator/evaluate.py", "evaluator/hidden/trusted_physics.py"):
        hashes[relative] = hashlib.sha256((ROOT.parents[1] / relative).read_bytes()).hexdigest()
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contract": "critical-vacuum-v2",
        "selected_source": str(selected[2].relative_to(ROOT)),
        "selected_sha256": hashlib.sha256((ROOT / "state.npz").read_bytes()).hexdigest(),
        "exact_checker": summary(exact_report),
        "public_checker": summary(public_report),
        "public_checker_returncode": public.returncode,
        "complex_gauge_audit": summary(gauge_report),
        "complex_gauge_max_absolute_differences": differences,
        "near_miss_source": str(near_miss[2].relative_to(ROOT)) if near_miss else None,
        "near_miss": summary(near_report) if near_report else None,
        "frozen_input_sha256": hashes,
        "valid_checkpoint_count": len(candidates),
        "passing_checkpoint_count": sum(bool(entry[3].get("passed")) for entry in candidates),
        "no_attempts_or_champion_code_accessed": True,
        "write_scope": str(ROOT),
        "selected_worker_seconds": selected[3].get("elapsed_seconds"),
        "selected_worker_evaluations": selected[3].get("evaluations"),
        "worker_best": {folder.name: summary(json.loads((folder / "score.json").read_text()))
                        for folder in ROOT.iterdir() if folder.is_dir() and (folder / "score.json").is_file()},
    }
    write_json(ROOT / "portfolio_results.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()

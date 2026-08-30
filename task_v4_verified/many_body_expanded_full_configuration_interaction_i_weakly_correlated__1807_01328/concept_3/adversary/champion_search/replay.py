"""Trusted mount launcher and separate private scorer for exact champion replay."""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


SEARCH = Path(__file__).resolve().parent
ROOT = SEARCH.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name):
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Run name must contain only alphanumerics, underscores, or hyphens")
    directory = SEARCH / "runs" / name
    if directory.exists():
        raise RuntimeError("Use a new run name to preserve exact earlier replay artifacts")
    output = directory / "outputs"
    output.mkdir(parents=True)
    public = SEARCH / "sandbox_input"
    expected_files = {"reconstruct.py", "generator.py", "source_hashes.json", "challenge_features.npz", "replay_driver.py"}
    if {path.name for path in public.iterdir()} != expected_files or any(path.is_symlink() for path in public.iterdir()):
        raise RuntimeError("Unexpected file in feature-only sandbox mount")
    command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
               "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr",
               "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
               "--symlink", "usr/lib64", "/lib64", "--dir", "/etc",
               "--ro-bind", "/etc/alternatives", "/etc/alternatives",
               "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
               "--ro-bind", str(public), "/input", "--bind", str(output), "/output",
               "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp",
               "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "PYTHONHASHSEED", "0",
               "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
               "--setenv", "MKL_NUM_THREADS", "1", "--chdir", "/input",
               "/usr/bin/python3", "-I", "-B", "/input/replay_driver.py"]
    started = time.perf_counter()
    with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
        completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   close_fds=True, timeout=300)
    record = {"created_utc": datetime.now(timezone.utc).isoformat(), "command": command,
              "exit_code": completed.returncode, "runtime_seconds": time.perf_counter() - started,
              "wall_timeout_seconds": 300, "mount_policy": "read-only system runtime and feature-only input; output-only writable mount; separate PID/network namespaces",
              "input_sha256": {path.name: digest(path) for path in sorted(public.iterdir())},
              "private_truth_mounted": False, "official_score_invoked": False}
    (directory / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if completed.returncode:
        raise SystemExit(completed.returncode)


def measure(target, prediction):
    error = prediction - target
    return {"count": len(target), "rmse": float(np.sqrt(np.mean(error ** 2))),
            "maximum_absolute_error": float(np.max(np.abs(error))),
            "mae": float(np.mean(np.abs(error)))}


def score(name):
    directory = SEARCH / "runs" / name
    manifest = json.loads((SEARCH / "private/sampling_manifest.json").read_text())
    for relative, expected in manifest["protected_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError("Protected artifact changed: " + relative)
    if digest(SEARCH / "private/truth.npz") != manifest["truth_sha256"]:
        raise RuntimeError("Private truth checksum mismatch")
    with np.load(SEARCH / "private/truth.npz", allow_pickle=False) as archive:
        truth = dict(archive)
    with np.load(directory / "outputs/predictions.npz", allow_pickle=False) as archive:
        ids, predictions = archive["ids"], archive["tail"]
    if ids.shape != truth["ids"].shape or predictions.shape != ids.shape or len(np.unique(ids)) != len(ids):
        raise ValueError("Champion output shape or ID uniqueness failure")
    if set(ids.tolist()) != set(truth["ids"].tolist()):
        raise ValueError("Champion output ID set mismatch")
    positions = {identifier: index for index, identifier in enumerate(ids.tolist())}
    order = [positions[identifier] for identifier in truth["ids"].tolist()]
    predictions = predictions[order]
    diagnostics = json.loads((directory / "outputs/diagnostics.json").read_text())
    by_id = {record["id"]: record for record in diagnostics["records"]}
    valid = np.asarray([by_id[identifier]["status"] == "ok" for identifier in truth["ids"].tolist()]) & np.isfinite(predictions)
    with np.load(directory / "outputs/inferred_hopping.npz", allow_pickle=False) as archive:
        if not np.array_equal(archive["ids"], ids):
            raise ValueError("Recovered matrix ID order mismatch")
        hopping = archive["hopping"][order]
    cohort_metrics = {}
    for cohort in np.unique(truth["cohort"]):
        mask = (truth["cohort"] == cohort) & valid
        cohort_metrics[str(cohort)] = measure(truth["tail"][mask], predictions[mask]) if mask.any() else None
    family_metrics = {}
    for family in range(6):
        mask = (truth["family"] == family) & valid
        family_metrics[str(family)] = measure(truth["tail"][mask], predictions[mask]) if mask.any() else None
    records, failures = [], []
    for row, identifier in enumerate(truth["ids"].tolist()):
        record = {"id": identifier, "cohort": str(truth["cohort"][row]), "family": int(truth["family"][row]),
                  "n_pairs": int(truth["n_pairs"][row]), "n_virtual": int(truth["n_virtual"][row]),
                  "target": float(truth["tail"][row]), "status": by_id[identifier]["status"],
                  "prediction": float(predictions[row]) if valid[row] else None,
                  "absolute_error": abs(float(predictions[row] - truth["tail"][row])) if valid[row] else None,
                  "maximum_transfer_error": float(np.max(np.abs(hopping[row] - truth["hopping"][row]))) if valid[row] else None,
                  "champion": by_id[identifier]}
        records.append(record)
        if not valid[row] or record["absolute_error"] > 3e-5:
            failures.append(record)
    overall = measure(truth["tail"][valid], predictions[valid]) if valid.any() else None
    successful = [record for record in records if record["prediction"] is not None]
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "run": name,
               "champion_source": "attempts/v_1/reconstruct.py", "champion_source_sha256": manifest["source_sha256"]["reconstruct.py"],
               "algorithm_modified": False, "total_cases": len(ids), "independent_cases": 192, "rare_support_cases": 2,
               "valid_predictions": int(valid.sum()), "exceptions_or_nonfinite": int((~valid).sum()),
               "cases_exceeding_3e_minus_5": len(failures), "overall_successful_metrics": overall,
               "all_cases_valid": bool(valid.all()), "cohort_metrics": cohort_metrics, "family_metrics": family_metrics,
               "worst_family_rmse": max(value["rmse"] for value in family_metrics.values() if value is not None),
               "maximum_transfer_error": max(record["maximum_transfer_error"] for record in successful) if successful else None,
               "maximum_low_order_feature_residual": max(max(record["champion"]["diagnostics"][key] for key in
                   ("singleton_max_residual", "pair_max_residual", "triple_max_residual")) for record in successful) if successful else None,
               "ambiguous_pairs_handled": sum(record["champion"]["diagnostics"]["ambiguous_pairs"] for record in successful),
               "predictor_runtime_seconds": diagnostics["runtime_seconds"],
               "numerical_runtime_seconds": diagnostics["numerical_runtime_seconds"],
               "predictor_peak_rss_mib": diagnostics["peak_rss_mib"],
               "isolation_checks": diagnostics["isolation_checks_path_visible"],
               "default_champion_assets_visible": diagnostics["default_champion_assets_visible"],
               "source_hashes_verified": diagnostics["source_hashes"] == manifest["source_sha256"],
               "protected_files_unchanged": True, "official_score_consulted_or_duplicated": False,
               "new_participant_generation_created": False,
               "failure_root_causes": "No failures observed" if not failures else "See case_results.json for unchanged champion exceptions and numerical mismatches",
               "hardness_disposition": "reject_v1_as_hardness_candidate" if valid.all() and not failures else "review_observed_failures_before_disposition"}
    (directory / "case_results.json").write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")
    (directory / "score.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2, allow_nan=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "score"))
    parser.add_argument("--run-name", default="run_1")
    args = parser.parse_args()
    if args.action == "run":
        run(args.run_name)
    else:
        score(args.run_name)


if __name__ == "__main__":
    main()

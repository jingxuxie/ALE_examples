"""Privileged two-start continuation-free construction and independent certification."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
sys.path.insert(0, str(HIDDEN))
from physics import INPUT_KEYS, metrics
from reference_operator import ReferenceModel
from solver_core import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*")
    args = parser.parse_args()
    policy = json.loads((HIDDEN / "policy.json").read_text())
    records = json.loads((HIDDEN / "manifest.json").read_text())["cases"]
    directory = HIDDEN / "references"
    directory.mkdir(exist_ok=True)
    for record in records:
        if args.cases and record["case_id"] not in args.cases:
            continue
        path = HIDDEN / "cases" / (record["case_id"] + ".npz")
        with np.load(path, allow_pickle=False) as archive:
            instance = {key: archive[key] for key in INPUT_KEYS}
        started = time.process_time()
        model = ReferenceModel(instance)
        primary, renormalization, primary_info = solve(instance, model, initial_factor=1.0)
        secondary, secondary_z, secondary_info = solve(instance, model, initial_factor=2.7)
        measured = metrics(instance, primary, renormalization, primary)
        second_measured = metrics(instance, secondary, secondary_z, primary)
        certificate = {"case_id": record["case_id"], "family": record["family"],
                       "instance_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "linear_eigenvalue": record["linear_eigenvalue"],
                       "direct_sum_primary": measured, "direct_sum_second_start": second_measured,
                       "min_low_frequency_gap": float(primary[:, 0].min()),
                       "gap_scale_ratio": float(np.max(primary[:, 0]) / np.min(primary[:, 0])),
                       "cpu_seconds_including_direct_verification": time.process_time() - started,
                       "primary_solver": primary_info, "secondary_solver": secondary_info}
        valid = (record["linear_eigenvalue"] > 1 and measured["sign_correct"]
                 and measured["gap_residual"] < policy["reference_residual_max"]
                 and measured["z_residual"] < policy["reference_residual_max"]
                 and second_measured["gap_residual"] < policy["reference_residual_max"]
                 and second_measured["branch_error"] < 2e-6 and second_measured["sign_correct"])
        certificate["valid"] = bool(valid)
        (directory / (record["case_id"] + ".json")).write_text(json.dumps(certificate, indent=2) + "\n")
        print(json.dumps({key: value for key, value in certificate.items()
                          if key not in ("primary_solver", "secondary_solver")}), flush=True)
        if valid:
            np.savez_compressed(directory / (record["case_id"] + ".npz"), delta=primary, z=renormalization)


if __name__ == "__main__":
    main()

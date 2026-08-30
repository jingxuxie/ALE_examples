"""Bounded builder-only generation and independent full-grid branch certification."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np
from materials import make
from reference import refine

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from physics import direct_rows, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--cpu-seconds", type=int, required=True)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (arguments.cpu_seconds, arguments.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    started = time.process_time()
    plan = json.loads((SIDECAR / "plan.json").read_text())
    specification = plan["cases"][arguments.index]
    directory = SIDECAR / "cases" / specification["case_id"]
    directory.mkdir(parents=True)
    instance, metadata, modes = make(specification)
    integrated = (instance["coupling"].sum(axis=0) * instance["weights"]).sum(axis=1)
    metadata.update(integrated_lambda_min=float(integrated.min()), integrated_lambda_max=float(integrated.max()),
                    integrated_lambda_weighted_mean=float(np.dot(instance["weights"], integrated)),
                    no_padding=True, no_duplicated_patches=True, no_duplicated_phonon_modes=True,
                    finite_window_scope="Exact finite Matsubara window; no continuum convergence claim",
                    generation_cpu_seconds=time.process_time() - started)
    assert integrated.max() < 4
    assert len(np.unique(instance["omega"])) == len(instance["omega"])
    assert 17.15 < metadata["upper_frequency_over_max_phonon"] < 17.17
    assert min(metadata["smallest_to_largest_patch_singular_values"]) > 1e-10
    np.savez_compressed(directory / "instance.npz", **instance)
    np.savez_compressed(directory / "private_initial_modes.npz", modes=modes)
    metadata["instance_sha256"] = hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest()
    (directory / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"case_id": specification["case_id"], "phase": "generated", "cpu_seconds": time.process_time() - started,
                      "integrated_lambda_max": metadata["integrated_lambda_max"]}), flush=True)
    eigenvalues = np.array([record["eigenvalue"] for record in metadata["calibrations"]])
    prefactor = np.pi * float(instance["temperature"])
    amplitudes = 8 * prefactor * np.sqrt(np.abs(eigenvalues - 1))
    initial = np.sum(modes * amplitudes[:, None, None], axis=0)
    outputs = []
    histories = []
    for factor in (0.6, 1.7):
        delta, renormalization, history = refine(instance, factor * initial, iterations=20)
        outputs.append({"delta": delta, "z": renormalization})
        histories.append(history)
        np.savez_compressed(directory / ("oracle_" + str(len(outputs)) + ".npz"), delta=delta, z=renormalization)
        print(json.dumps({"case_id": specification["case_id"], "phase": "refined", "start_factor": factor,
                          "iterations": len(history), "cpu_seconds": time.process_time() - started}), flush=True)
    primary, secondary = outputs
    first = metrics(instance, primary["delta"], primary["z"], primary["delta"])
    second = metrics(instance, secondary["delta"], secondary["z"], primary["delta"])
    direct_first = direct_rows(instance, primary["delta"], primary["z"])
    direct_second = direct_rows(instance, secondary["delta"], secondary["z"])
    minimum = float(np.min(primary["delta"][:, 0]) / prefactor)
    amplitude = float(np.max(primary["delta"][:, 0]) / prefactor)
    valid = all(record["gap_residual"] < 5e-13 and record["z_residual"] < 5e-13
                for record in (first, second, direct_first, direct_second))
    valid = bool(valid and first["sign_correct"] and second["sign_correct"] and
                 second["branch_error"] < 2e-6 and amplitude > 1e-7 and minimum > 1e-9)
    certificate = {"valid": valid, "case_id": specification["case_id"],
                   "instance_sha256": metadata["instance_sha256"],
                   "primary_all_frequency": first, "second_start_all_frequency": second,
                   "primary_direct_rows": direct_first, "second_start_direct_rows": direct_second,
                   "normal_pairing_eigenvalue": metadata["linear_eigenvalue"],
                   "isolated_sheet_eigenvalues": eigenvalues.tolist(),
                   "nonzero_amplitude_over_piT": amplitude, "minimum_low_gap_over_piT": minimum,
                   "low_frequency_gap_ratio": amplitude / minimum,
                   "patches_with_frequency_sign_changes": int(np.sum(np.any(primary["delta"] < 0, axis=1))),
                   "initial_amplitude_factors": [0.6, 1.7], "histories": histories,
                   "reference_solver": "Builder-owned full-grid scaled Newton, no reduced-frequency model",
                   "verification": "Independent full-signed all-frequency convolution plus direct signed audit rows",
                   "private_linear_mode_starts": True, "joint_12_cpu_attainability": "not_asserted_by_this_offline_certificate",
                   "actual_v4_failure_claimed": False, "offline_cpu_seconds": time.process_time() - started}
    if valid:
        np.savez_compressed(directory / "reference.npz", **primary)
        certificate["reference_sha256"] = hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest()
    (directory / "certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({key: value for key, value in certificate.items() if key != "histories"}), flush=True)


if __name__ == "__main__":
    main()

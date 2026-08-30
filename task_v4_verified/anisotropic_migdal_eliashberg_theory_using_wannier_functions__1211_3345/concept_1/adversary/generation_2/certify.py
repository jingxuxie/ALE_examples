"""Two-start, independently checked nonzero-branch reference worker."""

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
from reference import refine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from physics import INPUT_KEYS, direct_rows, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--cpu-seconds", type=int, default=50)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (arguments.cpu_seconds, arguments.cpu_seconds + 1))
    started = time.process_time()
    directory = Path(arguments.case)
    with np.load(directory / "instance.npz", allow_pickle=False) as archive:
        instance = {key: archive[key] for key in INPUT_KEYS}
    metadata = json.loads((directory / "parameters.json").read_text())
    with np.load(directory / "private_initial_modes.npz", allow_pickle=False) as archive:
        modes = archive["modes"]
    eigenvalues = np.array([record["eigenvalue"] for record in metadata["calibrations"]])
    amplitudes = 8 * np.pi * float(instance["temperature"]) * np.sqrt(np.abs(eigenvalues - 1))
    initial = np.sum(modes * amplitudes[:, None, None], axis=0)
    outputs = []
    histories = []
    for factor in (0.6, 1.7):
        delta, renormalization, history = refine(instance, factor * initial)
        outputs.append({"delta": delta, "z": renormalization})
        histories.append(history)
        np.savez_compressed(directory / ("oracle_" + str(len(outputs)) + ".npz"), delta=delta, z=renormalization)
    primary, secondary = outputs
    first = metrics(instance, primary["delta"], primary["z"], primary["delta"])
    second = metrics(instance, secondary["delta"], secondary["z"], primary["delta"])
    direct_first = direct_rows(instance, primary["delta"], primary["z"])
    direct_second = direct_rows(instance, secondary["delta"], secondary["z"])
    amplitude = float(np.max(primary["delta"][:, 0]) / (np.pi * float(instance["temperature"])))
    minimum = float(np.min(primary["delta"][:, 0]) / (np.pi * float(instance["temperature"])))
    valid = all(record["gap_residual"] < 5e-11 and record["z_residual"] < 5e-11
                for record in (first, second, direct_first, direct_second))
    valid = bool(valid and first["sign_correct"] and second["sign_correct"] and
                 second["branch_error"] < 2e-6 and amplitude > 1e-7 and minimum > 1e-9)
    certificate = {"valid": valid, "case_id": metadata["case_id"],
                   "instance_sha256": hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest(),
                   "primary_all_frequency": first, "second_start_all_frequency": second,
                   "primary_direct_rows": direct_first, "second_start_direct_rows": direct_second,
                   "normal_pairing_eigenvalue": metadata["linear_eigenvalue"],
                   "isolated_sheet_eigenvalues": eigenvalues.tolist(),
                   "nonzero_amplitude_over_piT": amplitude, "minimum_low_gap_over_piT": minimum,
                   "low_frequency_gap_ratio": float(np.max(primary["delta"][:, 0]) / np.min(primary["delta"][:, 0])),
                   "patches_with_frequency_sign_changes": int(np.sum(np.any(primary["delta"] < 0, axis=1))),
                   "starting_amplitude_factors": [0.6, 1.7], "histories": histories,
                   "offline_cpu_seconds": time.process_time() - started,
                   "reference_solver": "independently authored full-grid scaled Newton, not previous fresh code",
                   "verification": "independent all-frequency full-signed convolution and direct signed rows",
                   "joint_12_cpu_attainability": "not_asserted_by_offline_reference"}
    if valid:
        np.savez_compressed(directory / "reference.npz", **primary)
        certificate["reference_sha256"] = hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest()
    (directory / "certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({key: value for key, value in certificate.items() if key != "histories"}), flush=True)


if __name__ == "__main__":
    main()

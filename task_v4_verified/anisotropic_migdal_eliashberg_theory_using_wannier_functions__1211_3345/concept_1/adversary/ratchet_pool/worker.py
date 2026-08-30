"""Trusted, CPU-bounded sidecar construction; every write stays in this pool."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--cpu-seconds", type=int, required=True)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (arguments.cpu_seconds, arguments.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    sys.dont_write_bytecode = True
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        os.environ[variable] = "1"
    pool = Path(__file__).resolve().parent
    root = pool.parents[1]
    sys.path.insert(0, str(root / "evaluator" / "hidden"))
    sys.path.insert(0, str(root / "champions"))
    import numpy as np
    from scipy.optimize import brentq
    from build_suite import leading, make_instance
    from physics import metrics
    from reference_operator import ReferenceModel
    from solver_core import solve

    specification = json.loads(Path(arguments.job).read_text())
    plan = json.loads((pool / "plan.json").read_text())
    directory = pool / "cases" / specification["case_id"]
    directory.mkdir(parents=True, exist_ok=True)
    started = time.process_time()
    instance, original_metadata = make_instance(specification["family"], specification["seed"], specification["index"])
    metadata = dict(original_metadata)
    metadata.update(specification)
    metadata["in_original_parameter_contract"] = specification["profile"] == "original"
    metadata["base_generator_metadata"] = original_metadata
    calibration = []
    if specification["profile"] == "low_temperature":
        maximum_phonon = float(instance["omega"].max())
        instance["omega"] = maximum_phonon * np.asarray(specification["mode_ratios"])
        instance["temperature"] = np.array(maximum_phonon / specification["max_phonon_over_temperature"])
        instance["n_freq"] = np.array(specification["n_freq"])
        frequencies = np.pi * float(instance["temperature"]) * (2 * np.arange(int(instance["n_freq"])) + 1)
        guess = 0.4 * maximum_phonon / (1 + (frequencies / maximum_phonon) ** 2)
        instance["initial_delta"] = np.broadcast_to(guess, (len(instance["weights"]), len(frequencies))).copy()
        if "target_linear_eigenvalue" in specification:
            base_coupling = instance["coupling"].copy()

            def spectral_difference(scale):
                instance["coupling"] = base_coupling * scale
                eigenvalue, vector = leading(instance)
                calibration.append({"coupling_multiplier": float(scale), "linear_eigenvalue": eigenvalue})
                return eigenvalue - specification["target_linear_eigenvalue"]

            multiplier = brentq(spectral_difference, 0.05, 8.0, xtol=2e-10, rtol=2e-10, maxiter=32)
            instance["coupling"] = base_coupling * multiplier
            metadata["critical_coupling_multiplier"] = float(multiplier)
        eigenvalue, vector = leading(instance)
        metadata["linear_eigenvalue"] = eigenvalue
    temperature = float(instance["temperature"])
    frequency_count = int(instance["n_freq"])
    maximum_phonon = float(instance["omega"].max())
    metadata.update({"temperature": temperature, "n_freq": frequency_count,
                     "mode_energies": instance["omega"].tolist(),
                     "phonon_ratio": float(instance["omega"].max() / instance["omega"].min()),
                     "min_phonon_over_temperature": float(instance["omega"].min() / temperature),
                     "max_phonon_over_temperature": maximum_phonon / temperature,
                     "max_frequency_over_max_phonon": float(np.pi * temperature * (2 * frequency_count - 1) / maximum_phonon),
                     "calibration": calibration, "generation_cpu_seconds": time.process_time() - started})
    np.testing.assert_allclose(instance["coupling"], instance["coupling"].transpose(0, 2, 1), rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(instance["coulomb"], instance["coulomb"].T, rtol=1e-13, atol=1e-13)
    if not (np.all(instance["weights"] > 0) and np.all(instance["coupling"] >= 0)
            and np.all(instance["coulomb"] >= 0) and np.isclose(instance["weights"].sum(), 1.0)
            and metadata["linear_eigenvalue"] > 1.000005):
        raise ValueError("invalid physical parameters or normal state not demonstrably unstable")
    instance_path = directory / "instance.npz"
    np.savez_compressed(instance_path, **instance)
    metadata["instance_sha256"] = hashlib.sha256(instance_path.read_bytes()).hexdigest()
    (directory / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
    model = ReferenceModel(instance)
    solver_budget = min(70.0, max(4.0, (arguments.cpu_seconds - time.process_time()) * 0.28))
    primary, primary_z, primary_info = solve(instance, model, cpu_budget=solver_budget, initial_factor=1.0)
    secondary, secondary_z, secondary_info = solve(instance, model, cpu_budget=solver_budget, initial_factor=2.7)
    direct_started = time.process_time()
    primary_metrics = metrics(instance, primary, primary_z, primary)
    secondary_metrics = metrics(instance, secondary, secondary_z, primary)
    gap_over_temperature = float(np.max(primary[:, 0]) / (np.pi * temperature))
    valid = (primary_metrics["gap_residual"] < plan["reference_gap_residual_max"]
             and primary_metrics["z_residual"] < plan["reference_z_residual_max"]
             and secondary_metrics["gap_residual"] < plan["reference_gap_residual_max"]
             and secondary_metrics["z_residual"] < plan["reference_z_residual_max"]
             and secondary_metrics["branch_error"] < plan["cross_start_branch_error_max"]
             and primary_metrics["sign_correct"] and secondary_metrics["sign_correct"]
             and gap_over_temperature > plan["minimum_primary_gap_over_pi_temperature"])
    certificate = {"case_id": specification["case_id"], "valid": bool(valid),
                   "instance_sha256": metadata["instance_sha256"],
                   "direct_sum_primary": primary_metrics, "direct_sum_second_start": secondary_metrics,
                   "primary_solver": primary_info, "secondary_solver": secondary_info,
                   "initial_factors": [1.0, 2.7],
                   "normal_state_pairing_eigenvalue": metadata["linear_eigenvalue"],
                   "max_low_frequency_gap_over_pi_temperature": gap_over_temperature,
                   "min_low_frequency_gap": float(primary[:, 0].min()),
                   "max_low_frequency_gap": float(primary[:, 0].max()),
                   "low_frequency_gap_ratio": float(primary[:, 0].max() / primary[:, 0].min()),
                   "independent_direct_verification_cpu_seconds": time.process_time() - direct_started,
                   "total_worker_cpu_seconds": time.process_time(),
                   "joint_12_cpu_second_attainability": "not_established_by_offline_certification"}
    output_name = "reference.npz" if valid else "uncertified_candidate.npz"
    np.savez_compressed(directory / output_name, delta=primary, z=primary_z)
    certificate["solution_sha256"] = hashlib.sha256((directory / output_name).read_bytes()).hexdigest()
    (directory / "certificate.json").write_text(json.dumps(certificate, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"case_id": specification["case_id"], "valid": bool(valid), "n_freq": frequency_count,
                      "primary_residual": primary_metrics["gap_residual"],
                      "cross_start_branch_error": secondary_metrics["branch_error"],
                      "worker_cpu_seconds": time.process_time()}), flush=True)


if __name__ == "__main__":
    main()

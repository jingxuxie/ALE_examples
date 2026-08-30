"""Privileged eigenmode-seeded cross-check, not a within-budget candidate witness."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np
from scipy.optimize import brentq
from scipy.sparse.linalg import LinearOperator, gmres

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from build_suite import leading
from reference_operator import ReferenceModel
from verification import direct_rows, metrics


def refine(model, initial):
    delta = initial.copy()
    history = []
    for iteration in range(24):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-12)[:, None]
        residual = (delta - mapped) / scale
        error = float(np.max(np.abs(residual)))
        history.append(error)
        if error < 2e-13:
            break
        derivative = model.linearize(delta)

        def action(direction):
            return (derivative(direction.reshape(model.shape) * scale) / scale).ravel()

        operator = LinearOperator((delta.size, delta.size), matvec=action, dtype=np.float64)
        correction, information = gmres(operator, -residual.ravel(), tol=2e-8, atol=0, restart=40, maxiter=5)
        correction = correction.reshape(model.shape) * scale
        damping = 1.0
        for trial_index in range(22):
            trial = delta + damping * correction
            if np.all(trial[:, 0] > 0) and np.max(np.abs(trial - model.map(trial)[1]) / scale) < error:
                delta = trial
                break
            damping *= 0.5
        else:
            raise RuntimeError("offline Newton line search failed")
    return {"delta": delta, "z": model.map(delta)[0]}, history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--cpu-seconds", type=int, default=300)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (args.cpu_seconds, args.cpu_seconds + 1))
    directory = PENDING / "probes" / args.case
    with np.load(directory / "instance.npz", allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    started = time.process_time()
    eigenvalue, vector = leading(instance)
    model = ReferenceModel(instance)
    normal_z = model.map(np.zeros(model.shape))[0]
    weight = instance["weights"][:, None] * normal_z / model.frequencies
    norm = np.sum(weight * vector ** 2)
    prefactor = np.pi * model.temperature

    def projected(log_amplitude):
        amplitude = np.exp(log_amplitude)
        delta = amplitude * vector
        return float(np.sum(weight * vector * (delta - model.map(delta)[1])) / (amplitude * norm))

    amplitude = np.exp(brentq(projected, np.log(prefactor * 1e-5), np.log(prefactor * 5), xtol=1e-7))
    primary, primary_history = refine(model, 0.85 * amplitude * vector)
    np.savez_compressed(directory / "oracle_primary.npz", **primary)
    secondary, secondary_history = refine(model, 1.45 * amplitude * vector)
    np.savez_compressed(directory / "oracle_secondary.npz", **secondary)
    first_metrics = metrics(instance, primary["delta"], primary["z"], primary["delta"])
    second_metrics = metrics(instance, secondary["delta"], secondary["z"], primary["delta"])
    first_direct = direct_rows(instance, primary["delta"], primary["z"])
    second_direct = direct_rows(instance, secondary["delta"], secondary["z"])
    valid = (first_metrics["gap_residual"] < 5e-11 and first_metrics["z_residual"] < 5e-11
             and second_metrics["gap_residual"] < 5e-11 and second_metrics["z_residual"] < 5e-11
             and second_metrics["branch_error"] < 2e-6 and first_metrics["sign_correct"] and second_metrics["sign_correct"]
             and first_direct["gap_residual"] < 5e-11 and first_direct["z_residual"] < 5e-11
             and second_direct["gap_residual"] < 5e-11 and second_direct["z_residual"] < 5e-11
             and np.max(primary["delta"][:, 0]) / prefactor > 1e-4 and eigenvalue > 1)
    certificate = {"valid": bool(valid), "case_id": args.case,
                   "instance_sha256": hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest(),
                   "primary_all_frequency": first_metrics, "second_start_all_frequency": second_metrics,
                   "primary_direct_rows": first_direct, "second_start_direct_rows": second_direct,
                   "initial_amplitude_factors": [0.85, 1.45], "eigenmode_amplitude": float(amplitude),
                   "normal_pairing_eigenvalue": eigenvalue, "primary_residual_history": primary_history,
                   "secondary_residual_history": secondary_history,
                   "nonzero_amplitude_over_piT": float(np.max(primary["delta"][:, 0]) / prefactor),
                   "offline_oracle_cpu_seconds": time.process_time() - started,
                   "independent_verifier": "full_signed_linear_convolution_and_direct_signed_rows",
                   "joint_12_second_attainability": "not_established_by_this_privileged_offline_run"}
    if valid:
        np.savez_compressed(directory / "reference.npz", **primary)
        certificate["reference_sha256"] = hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest()
    (directory / "oracle_certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps(certificate), flush=True)


if __name__ == "__main__":
    main()

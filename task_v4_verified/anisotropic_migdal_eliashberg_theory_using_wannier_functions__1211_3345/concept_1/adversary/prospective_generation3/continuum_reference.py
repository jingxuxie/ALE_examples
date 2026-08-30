"""Builder-only full-grid reference with exact precombined convolution symbols."""

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
from scipy.fft import irfft, rfft
from scipy.sparse.linalg import LinearOperator, eigsh, gmres
import reference

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from physics import direct_rows, metrics


class CombinedModel(reference.Model):
    def __init__(self, instance):
        super().__init__(instance)
        self.kernel_imaginary_relative = float(np.max(np.abs(self.kernel_fft.imag)) / np.max(np.abs(self.kernel_fft)))
        assert self.kernel_imaginary_relative < 1e-14
        self.symbol = np.einsum("sab,sf->abf", self.weighted_coupling, self.kernel_fft.real, optimize=True)

    def convolve(self, values, parity):
        extended = np.concatenate((parity * values[:, ::-1], values), axis=1)
        transformed = rfft(extended, n=self.fft_length, workers=1)
        mixed = np.einsum("abf,bf->af", self.symbol, transformed, optimize=False)
        result = irfft(mixed, n=self.fft_length, workers=1)
        return result[:, self.n_freq:2 * self.n_freq]


def leading(model, initial):
    inner = np.sqrt(model.weights[:, None] * model.normal_z / model.frequencies[None, :])

    def product(vector):
        delta = vector.reshape(model.shape) / inner
        ratio = delta / model.frequencies
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return (inner * np.pi * model.temperature * pairing / model.normal_z).ravel()

    operator = LinearOperator((inner.size, inner.size), matvec=product, dtype=float)
    values = eigsh(operator, k=1, which="LA", ncv=16, tol=2e-12, return_eigenvectors=False,
                   v0=(initial * inner).ravel(), maxiter=200)
    return float(values[0])


def refine(model, initial):
    delta = initial.copy()
    history = []
    recent = []
    for iteration in range(36):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-14)[:, None]
        residual = (delta - mapped) / scale
        derivative = model.linearize(delta)

        def product(direction):
            return (derivative(direction.reshape(model.shape) * scale) / scale).ravel()

        operator = LinearOperator((delta.size, delta.size), matvec=product, dtype=float)
        step, info = gmres(operator, -residual.ravel(), tol=1e-7, atol=0, restart=40, maxiter=5)
        step = step.reshape(model.shape) * scale
        fraction = 1.0
        decreasing = step[:, 0] < 0
        if np.any(decreasing):
            fraction = min(1, 0.9 * np.min(-delta[decreasing, 0] / step[decreasing, 0]))
        error = float(np.max(np.abs(residual)))
        change = float(np.max(np.abs(fraction * step) / scale))
        history.append({"iteration": iteration, "residual": error, "relative_step": change, "gmres_info": int(info)})
        delta += fraction * step
        if error < 2e-13 and change < 2e-7:
            recent.append(delta.copy())
            if len(recent) >= 2:
                delta = np.mean(recent[-2:], axis=0)
                break
    return {"delta": delta, "z": model.map(delta)[0]}, history


def audit_operator(instance):
    small = dict(instance, n_freq=np.array(128), initial_delta=instance["initial_delta"][:, :128])
    model = CombinedModel(small)
    original = reference.public.Model(small)
    values = np.random.default_rng(23081).normal(size=model.shape)
    errors = []
    for parity in (-1, 1):
        expected = original.convolve(values, parity)
        observed = model.convolve(values, parity)
        errors.append(float(np.max(np.abs(expected - observed)) / np.max(np.abs(expected))))
    assert max(errors) < 2e-13
    return {"odd_relative_error": errors[0], "even_relative_error": errors[1],
            "comparison": "unchanged public per-mode signed FFT versus builder precombined symbol; all supplied modes and patches"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--cpu-seconds", type=int, default=320)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (arguments.cpu_seconds, arguments.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    started = time.process_time()
    directory = SIDECAR / "continuum_cases" / arguments.case
    with np.load(directory / "instance.npz", allow_pickle=False) as archive:
        instance = {key: archive[key] for key in reference.public.INPUT_KEYS}
    operator_audit = audit_operator(instance)
    model = CombinedModel(instance)
    eigenvalue = leading(model, instance["initial_delta"])
    print(json.dumps({"case_id": arguments.case, "phase": "normal_instability", "eigenvalue": eigenvalue,
                      "cpu_seconds": time.process_time() - started}), flush=True)
    outputs, histories = [], []
    for factor in (0.65, 1.5):
        output, history = refine(model, factor * instance["initial_delta"])
        outputs.append(output)
        histories.append(history)
        np.savez_compressed(directory / ("oracle_" + str(len(outputs)) + ".npz"), **output)
        print(json.dumps({"case_id": arguments.case, "phase": "refined", "start_factor": factor,
                          "iterations": len(history), "residual": history[-1]["residual"],
                          "cpu_seconds": time.process_time() - started}), flush=True)
    primary, secondary = outputs
    first = metrics(instance, primary["delta"], primary["z"], primary["delta"])
    second = metrics(instance, secondary["delta"], secondary["z"], primary["delta"])
    direct_first = direct_rows(instance, primary["delta"], primary["z"])
    direct_second = direct_rows(instance, secondary["delta"], secondary["z"])
    minimum = float(np.min(primary["delta"][:, 0]) / (np.pi * model.temperature))
    amplitude = float(np.max(primary["delta"][:, 0]) / (np.pi * model.temperature))
    valid = all(record["gap_residual"] < 5e-12 and record["z_residual"] < 5e-12
                for record in (first, second, direct_first, direct_second))
    valid = bool(valid and eigenvalue > 1.0001 and first["sign_correct"] and second["sign_correct"] and
                 second["branch_error"] < 1e-6 and amplitude > 1e-3 and minimum > 1e-7)
    certificate = {"valid": valid, "case_id": arguments.case,
                   "instance_sha256": hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest(),
                   "primary_all_frequency": first, "second_start_all_frequency": second,
                   "primary_direct_rows": direct_first, "second_start_direct_rows": direct_second,
                   "normal_pairing_eigenvalue": eigenvalue, "normal_instability_not_near_machine_precision": eigenvalue - 1 > 1e-4,
                   "nonzero_amplitude_over_piT": amplitude, "minimum_low_gap_over_piT": minimum,
                   "low_frequency_gap_ratio": amplitude / minimum, "operator_audit": operator_audit,
                   "initial_amplitude_factors": [0.65, 1.5], "histories": histories,
                   "reference_solver": "Builder-owned exact full-grid scaled Newton with algebraically precombined phonon FFT symbols; no frequency interpolation, no spectral truncation, no fresh code imported",
                   "verification": "Independent uncombined all-mode full signed convolution and direct signed audit rows",
                   "offline_memory_limit_mib": 3072, "offline_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                   "offline_cpu_seconds": time.process_time() - started,
                   "joint_12_cpu_2gib_attainability": "not_established_by_offline_certificate"}
    if valid:
        np.savez_compressed(directory / "reference.npz", **primary)
        certificate["reference_sha256"] = hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest()
    (directory / "certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({key: value for key, value in certificate.items() if key != "histories"}), flush=True)


if __name__ == "__main__":
    main()

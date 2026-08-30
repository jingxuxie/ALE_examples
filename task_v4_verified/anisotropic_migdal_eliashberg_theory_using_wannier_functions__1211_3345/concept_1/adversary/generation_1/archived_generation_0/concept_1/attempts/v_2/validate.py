import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh

from solve import Model, solve


def direct_residual(instance, delta, renormalization):
    prefactor = np.pi * float(instance["temperature"])
    frequencies = prefactor * (2 * np.arange(int(instance["n_freq"])) + 1)
    radius = np.hypot(frequencies[None, :], delta)
    normal_ratio = frequencies[None, :] / radius
    anomalous_ratio = delta / radius
    normal = np.zeros_like(delta)
    pairing = np.zeros_like(delta)
    for energy, matrix in zip(instance["omega"], instance["coupling"]):
        difference = energy ** 2 / (energy ** 2 + (frequencies[:, None] - frequencies[None, :]) ** 2)
        addition = energy ** 2 / (energy ** 2 + (frequencies[:, None] + frequencies[None, :]) ** 2)
        weighted = matrix * instance["weights"][None, :]
        normal += weighted @ (normal_ratio @ (difference - addition).T)
        pairing += weighted @ (anomalous_ratio @ (difference + addition).T)
    pairing -= 2 * ((instance["coulomb"] * instance["weights"][None, :]) @ anomalous_ratio.sum(axis=1))[:, None]
    expected = 1 + prefactor * normal / frequencies[None, :]
    mapped = prefactor * pairing / expected
    scale = np.maximum(np.max(np.abs(delta), axis=1), prefactor * 1e-10)[:, None]
    return float(np.max(np.abs(delta - mapped) / scale)), float(np.max(np.abs(renormalization - expected) / np.maximum(expected, 1)))


def tune_critical(instance, target=1.00002):
    base = instance["coupling"].copy()
    initial = None
    factor = 1.0
    previous = None
    for iteration in range(12):
        instance["coupling"] = factor * base
        model = Model(instance)
        normal = model.map(np.zeros(model.shape))[0]
        transform = np.sqrt(model.weights[:, None] * normal / model.frequencies[None, :])

        def product(vector):
            direction = vector.reshape(model.shape) / transform
            ratio = direction / model.frequencies[None, :]
            paired = model.convolve(ratio, 1)
            paired -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
            return (model.prefactor * paired / normal * transform).ravel()

        operator = LinearOperator((normal.size, normal.size), matvec=product, dtype=np.float64)
        eigenvalues, eigenvectors = eigsh(operator, k=1, which="LA", tol=2e-11, v0=initial, ncv=20)
        leading = float(eigenvalues[0])
        initial = eigenvectors[:, 0]
        if abs(leading - target) < 1e-11:
            return leading
        if previous is None:
            updated = factor * target / leading
        else:
            updated = factor + (target - leading) * (factor - previous[0]) / (leading - previous[1])
        previous = (factor, leading)
        factor = updated
    raise RuntimeError("critical tuning did not converge")


def enlarge(instance, count=25, frequencies=2048):
    original_count = len(instance["weights"])
    indices = np.arange(count) % original_count
    multiplicity = np.bincount(indices, minlength=original_count)
    result = {key: value.copy() for key, value in instance.items()}
    result["weights"] = instance["weights"][indices] / multiplicity[indices]
    result["coupling"] = instance["coupling"][:, indices][:, :, indices]
    result["coulomb"] = instance["coulomb"][indices][:, indices]
    result["n_freq"] = np.array(frequencies)
    grid = np.pi * float(instance["temperature"]) * (2 * np.arange(frequencies) + 1)
    envelope = 0.4 * np.max(instance["omega"]) / (1 + (grid / np.max(instance["omega"])) ** 2)
    result["initial_delta"] = np.tile(envelope, (count, 1))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {}
    for family in ["multiband", "retardation", "critical", "weak_interband", "combined"]:
        with np.load(args.input / "examples" / (family + ".npz"), allow_pickle=False) as archive:
            instance = {key: np.array(archive[key], copy=True) for key in archive.files}
        started = time.process_time()
        delta, renormalization = solve(instance)
        elapsed = time.process_time() - started
        residuals = direct_residual(instance, delta, renormalization)
        alternate = {key: value.copy() for key, value in instance.items()}
        alternate["initial_delta"] *= 2.0
        other_delta, other_z = solve(alternate)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * float(instance["temperature"]) * 1e-10)[:, None]
        agreement = float(np.max(np.abs(delta - other_delta) / scale))
        result = {"cpu_seconds_excluding_imports": elapsed, "direct_residuals": residuals,
                  "two_start_distance": agreement, "positive_first_gaps": bool(np.all(delta[:, 0] > 0))}
        report[family] = result
        print(family, result, flush=True)
        assert residuals[0] <= 2e-8 and residuals[1] <= 2e-9
        assert agreement <= 2e-6 and result["positive_first_gaps"]
        large = enlarge(instance)
        if family in ("critical", "combined"):
            leading = tune_critical(large)
            print(family, "large pairing eigenvalue", leading, flush=True)
        started = time.process_time()
        large_delta, large_z = solve(large)
        elapsed = time.process_time() - started
        residuals = direct_residual(large, large_delta, large_z)
        result = {"cpu_seconds_excluding_imports": elapsed, "direct_residuals": residuals,
                  "shape": list(large_delta.shape), "positive_first_gaps": bool(np.all(large_delta[:, 0] > 0))}
        report[family + "_large"] = result
        print(family + "_large", result, flush=True)
        assert residuals[0] <= 2e-8 and residuals[1] <= 2e-9
        assert result["positive_first_gaps"]
        if family == "combined":
            np.savez(args.output.parent / "stress_combined_input.npz", **large)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

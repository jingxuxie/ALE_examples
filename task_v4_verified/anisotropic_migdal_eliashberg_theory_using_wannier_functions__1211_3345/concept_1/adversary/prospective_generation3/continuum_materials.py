"""Positive log-frequency spectral quadrature with independently varying anisotropy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np
from scipy.special import ndtr

SIDECAR = Path(__file__).resolve().parent


def symmetric(random, shape, low, high):
    values = random.uniform(low, high, shape)
    return (values + values.swapaxes(-1, -2)) / 2


def make(specification):
    random = np.random.default_rng(specification["seed"])
    patches = specification["patches"]
    modes = specification["n_modes"]
    count = specification["n_freq"]
    bands = len(specification["sheet_lambda"])
    assert patches % bands == 0
    labels = np.repeat(np.arange(bands), patches // bands)
    weights = np.exp(random.uniform(-1.4, 0.9, patches))
    weights /= weights.sum()
    angular = np.exp(random.uniform(-0.5, 0.5, patches))
    total = angular[:, None] * angular[None, :] * symmetric(random, (patches, patches), 0.5, 1.5)
    coulomb = np.zeros((patches, patches))
    for band, strength in enumerate(specification["sheet_lambda"]):
        selected = labels == band
        mass = weights[selected].sum()
        block = total[np.ix_(selected, selected)]
        block *= strength * mass / (weights[selected] @ block @ weights[selected])
        total[np.ix_(selected, selected)] = block
        repulsion = symmetric(random, block.shape, 0.75, 1.25)
        repulsion *= specification["sheet_coulomb"][band] * mass / (weights[selected] @ repulsion @ weights[selected])
        coulomb[np.ix_(selected, selected)] = repulsion
    for first in range(patches):
        for second in range(first + 1, patches):
            if labels[first] != labels[second]:
                total[first, second] = total[second, first] = specification["interband_factor"] * np.sqrt(total[first, first] * total[second, second])
    maximum = float(np.exp(random.uniform(np.log(3), np.log(25))))
    lower = -np.log(specification["mode_span"])
    peak_centers = np.array([0.10, 0.31, 0.53, 0.74, 0.93]) * (-lower) + lower
    centers = peak_centers[:, None, None] + symmetric(random, (5, patches, patches), -0.22, 0.22)
    widths = symmetric(random, (5, patches, patches), 0.12, 0.36)
    amplitudes = np.exp(symmetric(random, (5, patches, patches), -1.2, 1.0))
    normalization = np.sum(amplitudes * widths * np.sqrt(2 * np.pi) *
                           (ndtr(-centers / widths) - ndtr((lower - centers) / widths)), axis=0)

    def quadrature(order):
        nodes, quadrature_weights = np.polynomial.legendre.leggauss(order)
        locations = (nodes + 1) * (-lower) / 2 + lower
        quadrature_weights *= (-lower) / 2
        profile = np.sum(amplitudes[None, :] * np.exp(-0.5 *
                         ((locations[:, None, None, None] - centers[None, :]) / widths[None, :]) ** 2), axis=1)
        density = profile / normalization
        couplings = total[None, :] * quadrature_weights[:, None, None] * density
        correction = total / couplings.sum(axis=0)
        return maximum * np.exp(locations), couplings * correction[None, :], locations, quadrature_weights, correction

    energies, coupling, nodes, quadrature_weights, correction = quadrature(modes)
    higher_energies, higher_coupling, unused_nodes, unused_weights, unused_correction = quadrature(192)
    differences = maximum * np.geomspace(1e-5, 20, 80)
    kernels = energies[:, None] ** 2 / (energies[:, None] ** 2 + differences[None, :] ** 2)
    higher_kernels = higher_energies[:, None] ** 2 / (higher_energies[:, None] ** 2 + differences[None, :] ** 2)
    sampled = np.einsum("sab,sk->abk", coupling, kernels)
    comparison = np.einsum("sab,sk->abk", higher_coupling, higher_kernels)
    quadrature_error = float(np.max(np.abs(sampled - comparison) / total[:, :, None]))
    temperature = maximum / specification["max_phonon_over_temperature"]
    frequencies = np.pi * temperature * (2 * np.arange(count) + 1)
    initial = np.broadcast_to(0.4 * maximum / (1 + (frequencies / maximum) ** 2), (patches, count)).copy()
    permutation = random.permutation(patches)
    coupling = coupling[:, permutation][:, :, permutation]
    coulomb = coulomb[np.ix_(permutation, permutation)]
    weights = weights[permutation]
    total = total[np.ix_(permutation, permutation)]
    integrated = total @ weights
    spectra = np.linalg.svd(coupling.reshape(modes, -1), compute_uv=False)
    selected = np.argsort(coupling.sum(axis=(1, 2)))[-8:]
    commutators = []
    for first in selected:
        for second in selected:
            left, right = coupling[first], coupling[second]
            commutators.append(float(np.linalg.norm(left @ right - right @ left) /
                                     (np.linalg.norm(left) * np.linalg.norm(right))))
    patch_ranks = [float(values[-1] / values[0]) for values in
                   (np.linalg.svd(matrix, compute_uv=False) for matrix in coupling)]
    instance = {"temperature": np.array(temperature), "n_freq": np.array(count), "weights": weights,
                "omega": energies, "coupling": coupling, "coulomb": coulomb, "initial_delta": initial}
    metadata = dict(specification, bands=bands, band=labels[permutation].tolist(),
                    temperature=temperature, phonon_window=[maximum / specification["mode_span"], maximum],
                    finite_cutoff_over_physical_phonon_upper=float(frequencies[-1] / maximum),
                    finite_cutoff_over_largest_quadrature_node=float(frequencies[-1] / energies[-1]),
                    integrated_lambda_min=float(integrated.min()), integrated_lambda_max=float(integrated.max()),
                    integrated_lambda_weighted_mean=float(weights @ integrated),
                    spectral_matrix_rank_relative_1e_8=int(np.sum(spectra > spectra[0] * 1e-8)),
                    spectral_matrix_singular_ratios=(spectra / spectra[0]).tolist(),
                    maximum_relative_noncommutator=max(commutators), minimum_patch_singular_ratio=min(patch_ranks),
                    normalized_kernel_difference_vs_192_bins=quadrature_error,
                    maximum_integrated_quadrature_renormalization=float(np.max(np.abs(correction - 1))),
                    quadrature="Gauss-Legendre in log(Omega), five positive smooth pair-dependent Gaussian peaks; per-pair weights normalized to fixed integrated lambda",
                    alpha2F_convention="coupling_s = 2 alpha2F(Omega_s) * dlog(Omega)_s; the exact scored finite quadrature is the supplied mode sum",
                    physical_scope="Synthetic finite-cutoff anisotropic phonon materials. No continuum or microscopic material accuracy claim. Distinct physical spectral bins, no padding or repeated modes.")
    spectral_parameters = {"centers": centers, "widths": widths, "amplitudes": amplitudes,
                           "log_nodes": nodes, "log_quadrature_weights": quadrature_weights,
                           "patch_permutation": permutation, "integrated_coupling": total}
    return instance, metadata, spectral_parameters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", action="append", default=[])
    arguments = parser.parse_args()
    started = time.process_time()
    plan = json.loads((SIDECAR / "continuum_plan.json").read_text())
    records = []
    for specification in plan["cases"]:
        if arguments.case_id and specification["case_id"] not in arguments.case_id:
            continue
        directory = SIDECAR / "continuum_cases" / specification["case_id"]
        directory.mkdir(parents=True, exist_ok=False)
        instance, metadata, parameters = make(specification)
        np.savez_compressed(directory / "instance.npz", **instance)
        np.savez_compressed(directory / "spectral_parameters.npz", **parameters)
        metadata["instance_sha256"] = hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest()
        (directory / "parameters.json").write_text(json.dumps(metadata, indent=2) + "\n")
        record = {key: metadata[key] for key in ("case_id", "n_freq", "patches", "n_modes", "integrated_lambda_max", "spectral_matrix_rank_relative_1e_8", "maximum_relative_noncommutator", "normalized_kernel_difference_vs_192_bins")}
        records.append(record)
        print(json.dumps(record), flush=True)
    output_path = SIDECAR / "continuum_generation.json"
    elapsed = time.process_time() - started
    previous = json.loads(output_path.read_text()) if output_path.exists() else {"cases": [], "cpu_seconds": 0}
    previous_runs = previous.get("runs", [{"case_ids": [item["case_id"] for item in previous["cases"]],
                                            "cpu_seconds": previous["cpu_seconds"]}])
    result = {"cases": previous["cases"] + records, "cpu_seconds": previous["cpu_seconds"] + elapsed,
              "runs": previous_runs + [{"case_ids": [item["case_id"] for item in records], "cpu_seconds": elapsed}]}
    output_path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

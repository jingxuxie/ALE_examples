import argparse
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh_tridiagonal


ROOT = Path(__file__).resolve().parent
TASK = ROOT.parents[1]
PRIVATE = TASK / "pilots/activation/private"
TRUSTED = PRIVATE / "reference/initial/initial_domain_wall_01_731101"
sys.path.insert(0, str(PRIVATE))
from build_references import spirit_config, set_spins
from spirit import chain, htst, simulation, state, system
from spirit.parameters import gneb, llg


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def energy_gradient(case, spins):
    exchange = np.asarray(case["exchange_meV"])
    tensor = np.asarray(case["anisotropy_meV"])
    field = np.asarray(case["field_meV"])
    tensor_spins = np.einsum("nij,nj->ni", tensor, spins)
    terms = -np.sum(spins * tensor_spins + spins * field, axis=1)
    terms[:-1] -= exchange * np.sum(spins[:-1] * spins[1:], axis=1)
    gradient = -2 * tensor_spins - field
    gradient[:-1] -= exchange[:, None] * spins[1:]
    gradient[1:] -= exchange[:, None] * spins[:-1]
    return terms, gradient


def blocks(case, spins):
    tensor = np.asarray(case["anisotropy_meV"])
    exchange = np.asarray(case["exchange_meV"])
    _, gradient = energy_gradient(case, spins)
    polar = np.column_stack((spins[:, 2], np.zeros(len(spins)), -spins[:, 0]))
    multiplier = np.sum(spins * gradient, axis=1)
    diagonal_polar = -2 * np.einsum("ni,nij,nj->n", polar, tensor, polar) - multiplier
    diagonal_normal = -2 * tensor[:, 1, 1] - multiplier
    off_polar = -exchange * np.sum(polar[:-1] * polar[1:], axis=1)
    return [(diagonal_polar, off_polar), (diagonal_normal, -exchange)], polar


def diagnose(case, spins, full_spectrum=True):
    terms, gradient = energy_gradient(case, spins)
    tangent = gradient - np.sum(gradient * spins, axis=1)[:, None] * spins
    matrices, _ = blocks(case, spins)
    spectra = []
    for diagonal, offdiagonal in matrices:
        options = {} if full_spectrum else {"select": "i", "select_range": (0, 1)}
        spectra.append(eigh_tridiagonal(diagonal, offdiagonal, eigvals_only=True, check_finite=False, **options))
    eigenvalues = np.sort(np.concatenate(spectra))
    return {"energy_meV": float(terms.sum()), "residual_meV": float(np.max(np.linalg.norm(tangent, axis=1))),
            "normal_component": float(np.max(np.abs(spins[:, 1]))), "eigenvalues": eigenvalues}


def hessian_fd_error(case, spins):
    matrices, polar = blocks(case, spins)
    random = np.random.default_rng(319)
    coordinates = random.normal(size=(len(spins), 2))
    coordinates /= np.linalg.norm(coordinates)
    direction = polar * coordinates[:, :1]
    direction[:, 1] = coordinates[:, 1]
    epsilon = 2e-5
    positive, negative = spins + epsilon * direction, spins - epsilon * direction
    positive /= np.linalg.norm(positive, axis=1)[:, None]
    negative /= np.linalg.norm(negative, axis=1)[:, None]
    gradient = energy_gradient(case, spins)[1]
    derivative = (energy_gradient(case, positive)[1] - energy_gradient(case, negative)[1]) / (2 * epsilon)
    derivative -= np.sum(spins * gradient, axis=1)[:, None] * direction
    actual = np.column_stack((np.sum(derivative * polar, axis=1), derivative[:, 1]))
    expected = np.empty_like(actual)
    for component, (diagonal, offdiagonal) in enumerate(matrices):
        expected[:, component] = diagonal * coordinates[:, component]
        expected[:-1, component] += offdiagonal * coordinates[1:, component]
        expected[1:, component] += offdiagonal * coordinates[:-1, component]
    return float(np.max(np.abs(actual - expected)))


def extended_case(count):
    case = json.loads((TRUSTED / "case.json").read_text())
    answer = json.loads((TRUSTED / "solution.json").read_text())
    original_count = case["n_spins"]
    if count < original_count:
        raise ValueError("continuation only extends the trusted N=40 case")
    minimum_a = np.asarray(case["minimum_a"])
    minimum_b = np.asarray(case["minimum_b"])
    saddle = np.asarray(answer["saddle"])
    def extend(values, bulk):
        return np.concatenate((values, np.tile(bulk, (count - original_count, 1))))
    case["case_id"] = f"source_scale_domain_wall_N{count}"
    case["n_spins"] = count
    case["exchange_meV"] += [case["exchange_meV"][-1]] * (count - original_count)
    case["anisotropy_meV"] += [case["anisotropy_meV"][-1]] * (count - original_count)
    case["minimum_a"] = extend(minimum_a, minimum_a[-1]).tolist()
    case["minimum_b"] = extend(minimum_b, minimum_b[-1]).tolist()
    case["temperature_K"] = 0.5
    saddle = extend(saddle, minimum_a[-1])
    return case, saddle


def build(count):
    directory = ROOT / f"N{count}"
    directory.mkdir(exist_ok=True)
    case, saddle_seed = extended_case(count)
    config = directory / "spirit.cfg"
    config.write_text(spirit_config(case))
    minimum_a = np.asarray(case["minimum_a"])
    minimum_b = np.asarray(case["minimum_b"])
    begin = time.perf_counter()
    times = {}
    initial = diagnose(case, saddle_seed, False)
    print(f"N={count} setup; seed residual={initial['residual_meV']:.3g}", flush=True)
    with state.State(str(config), quiet=True) as pointer:
        times["setup"] = time.perf_counter() - begin
        chain.image_to_clipboard(pointer)
        chain.set_length(pointer, 3)
        for image, spins in enumerate([minimum_a, saddle_seed, minimum_b]):
            set_spins(pointer, spins, image)
        gneb.set_image_type_automatically(pointer)
        gneb.set_convergence(pointer, 1e-11)
        started = time.perf_counter()
        simulation.start(pointer, simulation.METHOD_GNEB, simulation.SOLVER_LBFGS_OSO, n_iterations=2000)
        times["native_gneb_confirmation"] = time.perf_counter() - started
        saddle = system.get_spin_directions(pointer, idx_image=1).copy()
        started = time.perf_counter()
        saddle_info = diagnose(case, saddle)
        minimum_info = diagnose(case, minimum_a)
        times["full_tridiagonal_spectra"] = time.perf_counter() - started
        if max(saddle_info["residual_meV"], minimum_info["residual_meV"]) > 2e-6:
            raise RuntimeError("stationarity failed")
        if saddle_info["normal_component"] > 1e-12 or saddle_info["eigenvalues"][0] >= -1e-6 or saddle_info["eigenvalues"][1] <= 1e-6 or minimum_info["eigenvalues"][0] <= 1e-6:
            raise RuntimeError("planarity/inertia failed")
        log_omega = float(0.5 * (np.log(minimum_info["eigenvalues"]).sum() - np.log(saddle_info["eigenvalues"][1:]).sum()))
        dense_check = None
        if count <= 128:
            started = time.perf_counter()
            htst.calculate(pointer, 0, 1, n_eigenmodes_keep=2, sparse=False)
            native_dense = htst.get_info_dict(pointer)
            dense_check = {"native": native_dense,
                           "minimum_spectrum_max_error": float(np.max(np.abs(np.asarray(htst.get_eigenvalues_min(pointer)) - minimum_info["eigenvalues"]))),
                           "saddle_spectrum_max_error": float(np.max(np.abs(np.asarray(htst.get_eigenvalues_sp(pointer)) - saddle_info["eigenvalues"]))) }
            times["native_dense_htst_check"] = time.perf_counter() - started
            if max(dense_check["minimum_spectrum_max_error"], dense_check["saddle_spectrum_max_error"]) > 1e-4:
                raise RuntimeError("native dense spectrum mismatch")
        print(f"N={count} native sparse HTST", flush=True)
        started = time.perf_counter()
        htst.calculate(pointer, 0, 1, n_eigenmodes_keep=0, sparse=True)
        native_sparse = htst.get_info_dict(pointer)
        times["native_sparse_htst"] = time.perf_counter() - started
        if native_sparse["Omega_0"] <= 0 or not np.isfinite(native_sparse["prefactor"]) or native_sparse["temperature_exponent"] != 0:
            raise RuntimeError(f"invalid native sparse HTST: {native_sparse}")
        omega_error = abs(float(np.log(native_sparse["Omega_0"])) - log_omega)
        if omega_error > 2e-5:
            raise RuntimeError(f"native sparse determinant mismatch {omega_error}")
        saddle_terms = energy_gradient(case, saddle)[0]
        minimum_terms = energy_gradient(case, minimum_a)[0]
        barrier = float(np.sum(saddle_terms - minimum_terms))
        native_minimum_energy = float(system.get_energy(pointer, idx_image=0))
        native_saddle_energy = float(system.get_energy(pointer, idx_image=1))
        native_barrier = native_saddle_energy - native_minimum_energy
        rounding_bound = float(np.finfo(np.float32).eps * (abs(native_minimum_energy) + abs(native_saddle_energy)))
        if abs(native_barrier - barrier) > rounding_bound:
            raise RuntimeError("native energy disagreement exceeds float32 rounding bound")
        fd_error = hessian_fd_error(case, saddle)
        if fd_error > 1e-6:
            raise RuntimeError("finite-difference Hessian mismatch")
        matrices, polar = blocks(case, saddle)
        _, vector = eigh_tridiagonal(*matrices[0], select="i", select_range=(0, 0), check_finite=False)
        unstable = polar * vector[:, :1]
        branches = []
        print(f"N={count} native downhill connectivity", flush=True)
        for sign in [-1, 1]:
            perturbed = saddle + sign * 0.025 * unstable
            perturbed /= np.linalg.norm(perturbed, axis=1)[:, None]
            set_spins(pointer, perturbed, 2)
            llg.set_convergence(pointer, 1e-8, idx_image=2)
            started = time.perf_counter()
            simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=100000, idx_image=2)
            relaxed = system.get_spin_directions(pointer, idx_image=2).copy()
            distances = [float(np.max(np.linalg.norm(relaxed - endpoint, axis=1))) for endpoint in [minimum_a, minimum_b]]
            branch_residual = diagnose(case, relaxed, False)["residual_meV"]
            branches.append({"sign": sign, "endpoint_distances": distances, "residual_meV": branch_residual, "seconds": time.perf_counter() - started})
        if np.argmin(branches[0]["endpoint_distances"]) == np.argmin(branches[1]["endpoint_distances"]) or max(min(branch["endpoint_distances"]) for branch in branches) > 2e-4:
            write_json(directory / "failed_connectivity.json", branches)
            raise RuntimeError(f"native downhill connectivity failed {branches}")
        result = {"saddle": saddle, "barrier_meV": barrier, "eigenvalues_min_meV": minimum_info["eigenvalues"], "eigenvalues_saddle_meV": saddle_info["eigenvalues"], "log_omega0": log_omega}
        np.savez_compressed(directory / "reference.npz", **result)
        write_json(directory / "case.json", case)
        report = {"n_spins": count, "validated": True, "reference_wall_seconds": time.perf_counter() - begin,
                  "peak_rss_kib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "stage_seconds": times,
                  "saddle_residual_meV": saddle_info["residual_meV"], "minimum_residual_meV": minimum_info["residual_meV"],
                  "saddle_first_eigenvalues_meV": saddle_info["eigenvalues"][:6].tolist(), "minimum_lowest_eigenvalue_meV": float(minimum_info["eigenvalues"][0]),
                  "barrier_meV": barrier, "native_barrier_meV": native_barrier, "native_barrier_rounding_bound_meV": rounding_bound,
                  "log_omega0": log_omega, "native_sparse": native_sparse, "native_sparse_log_omega_error": omega_error,
                  "dense_crosscheck": dense_check, "hessian_fd_max_error": fd_error, "downhill_branches": branches,
                  "continuation_seed_residual_meV": initial["residual_meV"], "native_gneb_seed_max_spin_change": float(np.max(np.linalg.norm(saddle - saddle_seed, axis=1))),
                  "barrier_contribution_after_site_40_meV": float(np.sum((saddle_terms - minimum_terms)[40:])),
                  "barrier_over_kBT_at_0p5K": barrier / (0.08617333262 * 0.5), "source_revision": "e82250d3b14411c2c2fa292d143f13e3e111ad8c",
                  "trusted_seed_sha256": hashlib.sha256((TRUSTED / "solution.json").read_bytes()).hexdigest()}
        write_json(directory / "validation.json", report)
        print(f"VALIDATED N={count} wall={report['reference_wall_seconds']:.3f}s barrier={barrier:.9f} sparse_error={omega_error:.3g}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[40, 128, 512, 2048])
    arguments = parser.parse_args()
    os.chdir(ROOT)
    for size in arguments.sizes:
        build(size)

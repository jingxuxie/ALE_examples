import argparse
import hashlib
import json
import os
import resource
import time

import numpy as np
from scipy.linalg import eigh_tridiagonal

import build
from spirit import chain, htst, simulation, state, system
from spirit.parameters import gneb, llg

reference = build.reference


def connect(pointer, case, saddle):
    matrices, polar = reference.blocks(case, saddle)
    _, vector = eigh_tridiagonal(*matrices[0], select="i", select_range=(0, 0), check_finite=False)
    unstable = polar * vector[:, :1]
    endpoints = [np.asarray(case["minimum_a"]), np.asarray(case["minimum_b"])]
    branches = []
    for sign in [-1, 1]:
        perturbed = saddle + sign * 0.025 * unstable
        perturbed /= np.linalg.norm(perturbed, axis=1)[:, None]
        reference.set_spins(pointer, perturbed, 2)
        llg.set_convergence(pointer, 1e-8, idx_image=2)
        started = time.perf_counter()
        simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=100000, idx_image=2)
        relaxed = system.get_spin_directions(pointer, idx_image=2).copy()
        branches.append({"sign": sign, "endpoint_distances": [float(np.max(np.linalg.norm(relaxed - endpoint, axis=1))) for endpoint in endpoints], "residual_meV": reference.diagnose(case, relaxed, False)["residual_meV"], "seconds": time.perf_counter() - started})
    if np.argmin(branches[0]["endpoint_distances"]) == np.argmin(branches[1]["endpoint_distances"]) or max(min(branch["endpoint_distances"]) for branch in branches) > 2e-4:
        raise RuntimeError(f"native connectivity failed: {branches}")
    return branches


def certify(family, seed, count):
    started = time.perf_counter()
    identifier = f"ratchet1_challenge_{family}_{seed}"
    directory = build.ROOT / "challenge" / identifier
    directory.mkdir(parents=True, exist_ok=True)
    os.chdir(directory)
    print(f"BEGIN LARGE {identifier} N={count}", flush=True)
    small_case, small_seed, _ = build.prepared_case(family, seed, 128, "challenge", directory / "small_calibration")
    _, small_validation, small_location = build.native_branch(small_case, small_seed, directory / "small_calibration")
    small_right = build.right_seed(small_case, family, small_seed)
    _, _, small_right_location = build.native_branch(small_case, small_right, directory / "small_right_calibration")
    case, left_seed, preparation = build.prepared_case(family, seed, count, "challenge", directory / "full_native")
    right_seed = build.right_seed(case, family, left_seed)
    location = directory / "full_native"
    config = location / "spirit.cfg"
    config.write_text(reference.spirit_config(case))
    minimum_a = np.asarray(case["minimum_a"])
    minimum_b = np.asarray(case["minimum_b"])
    stage = {}
    stage_started = time.perf_counter()
    minimum_info = reference.diagnose(case, minimum_a)
    minimum_b_info = reference.diagnose(case, minimum_b, False)
    stage["independent_minimum_spectra"] = time.perf_counter() - stage_started
    if minimum_info["eigenvalues"][0] <= 1e-6 or minimum_b_info["eigenvalues"][0] <= 1e-6:
        raise RuntimeError("invalid endpoint inertia")
    candidates = []
    stage_started = time.perf_counter()
    with state.State(str(config), quiet=True) as pointer:
        chain.image_to_clipboard(pointer)
        chain.set_length(pointer, 3)
        stage["native_shared_setup"] = time.perf_counter() - stage_started
        for mechanism, seed_spins in [("left_nucleation", left_seed), ("right_nucleation", right_seed)]:
            branch_started = time.perf_counter()
            for image, spins in enumerate([minimum_a, seed_spins, minimum_b]):
                reference.set_spins(pointer, spins, image)
            gneb.set_image_type_automatically(pointer)
            gneb.set_convergence(pointer, 1e-11)
            stage_started = time.perf_counter()
            simulation.start(pointer, simulation.METHOD_GNEB, simulation.SOLVER_LBFGS_OSO, n_iterations=2000)
            gneb_seconds = time.perf_counter() - stage_started
            saddle = system.get_spin_directions(pointer, idx_image=1).copy()
            stage_started = time.perf_counter()
            info = reference.diagnose(case, saddle)
            spectrum_seconds = time.perf_counter() - stage_started
            if info["residual_meV"] > 2e-6 or info["normal_component"] > 1e-12 or info["eigenvalues"][0] >= -1e-6 or info["eigenvalues"][1] <= 1e-6:
                raise RuntimeError(f"native {mechanism} stationarity/inertia failed")
            terms = reference.energy_gradient(case, saddle)[0] - reference.energy_gradient(case, minimum_a)[0]
            barrier = float(np.sum(terms))
            native_energy_a = float(system.get_energy(pointer, idx_image=0))
            native_energy_s = float(system.get_energy(pointer, idx_image=1))
            rounding_bound = float(np.finfo(np.float32).eps * (abs(native_energy_a) + abs(native_energy_s)))
            if abs(native_energy_s - native_energy_a - barrier) > rounding_bound:
                raise RuntimeError("native energy discrepancy exceeds getter rounding bound")
            fd_error = reference.hessian_fd_error(case, saddle)
            if fd_error > 1e-6:
                raise RuntimeError("independent finite-difference Hessian mismatch")
            branches = connect(pointer, case, saddle)
            info_record = {"mechanism": mechanism, "validated": True, "barrier_meV": barrier, "saddle_residual_meV": info["residual_meV"], "minimum_residual_meV": minimum_info["residual_meV"], "saddle_first_eigenvalues_meV": info["eigenvalues"][:6].tolist(), "minimum_lowest_eigenvalue_meV": float(minimum_info["eigenvalues"][0]), "native_barrier_meV": native_energy_s - native_energy_a, "native_barrier_rounding_bound_meV": rounding_bound, "hessian_fd_max_error": fd_error, "downhill_branches": branches, "continuation_seed_residual_meV": reference.diagnose(case, seed_spins, False)["residual_meV"], "native_gneb_seed_max_spin_change": float(np.max(np.linalg.norm(saddle - seed_spins, axis=1))), "barrier_contribution_after_site_40_meV": float(np.sum(terms[40:])), "native_gneb_seconds": gneb_seconds, "full_saddle_spectrum_seconds": spectrum_seconds, "whole_branch_seconds": time.perf_counter() - branch_started, "native_sparse_htst_note": "Only selected lower mechanism receives full-size sparse HTST; both mechanisms have native dense/sparse HTST at N128, full-size GNEB, independent inertia/FD and native connectivity."}
            mechanism_directory = directory / "mechanisms" / mechanism
            reference.write_json(mechanism_directory / "validation.json", info_record)
            np.savez_compressed(mechanism_directory / "saddle.npz", saddle=saddle)
            candidates.append((info_record, saddle, info["eigenvalues"]))
            print(f"N={count} {mechanism} connected barrier={barrier:.9f}", flush=True)
        record, saddle, eigenvalues = min(candidates, key=lambda item: item[0]["barrier_meV"])
        for image, spins in enumerate([minimum_a, saddle, minimum_b]):
            reference.set_spins(pointer, spins, image)
        log_omega = float(0.5 * (np.log(minimum_info["eigenvalues"]).sum() - np.log(eigenvalues[1:]).sum()))
        print(f"N={count} native sparse HTST selected={record['mechanism']}", flush=True)
        stage_started = time.perf_counter()
        htst.calculate(pointer, 0, 1, n_eigenmodes_keep=0, sparse=True)
        native = htst.get_info_dict(pointer)
        stage["native_sparse_htst"] = time.perf_counter() - stage_started
        if native["Omega_0"] <= 0 or not np.isfinite(native["prefactor"]) or native["temperature_exponent"] != 0:
            raise RuntimeError(f"native sparse HTST failed: {native}")
        omega_error = abs(float(np.log(native["Omega_0"])) - log_omega)
        if omega_error > 2e-5:
            raise RuntimeError("native sparse Omega0 mismatch")
    elapsed = time.perf_counter() - started
    if elapsed >= 90:
        raise RuntimeError(f"complete native author reference exceeds90s: {elapsed}")
    solution = {"saddle": saddle.tolist(), "barrier_meV": record["barrier_meV"], "eigenvalues_min_meV": minimum_info["eigenvalues"].tolist(), "eigenvalues_saddle_meV": eigenvalues.tolist(), "log_omega0": log_omega}
    mechanisms = [{"mechanism": candidate[0]["mechanism"], "validated": True, "barrier_meV": candidate[0]["barrier_meV"], "validation_path": str((directory / "mechanisms" / candidate[0]["mechanism"] / "validation.json").relative_to(build.RATCHET))} for candidate in candidates]
    validation = {**record, "case_id": identifier, "family": family, "seed": seed, "n_spins": count, "reference_runtime_seconds": elapsed, "reference_wall_seconds": elapsed, "stage_seconds": stage, "native_sparse": native, "native_sparse_log_omega_error": omega_error, "log_omega0": log_omega, "dense_crosscheck": None, "same_parameter_small_dense_crosscheck": {"path": str((small_location / "validation.json").relative_to(build.RATCHET)), "native_dense": small_validation["dense_crosscheck"], "right_mechanism_path": str((small_right_location / "validation.json").relative_to(build.RATCHET))}, "minimum_b_lowest_eigenvalue_meV": float(minimum_b_info["eigenvalues"][0]), "native_preparation": preparation, "parameter_perturbations": preparation["parameter_perturbations"], "competing_mechanisms": mechanisms, "selected_native_artifacts": str(location.relative_to(build.RATCHET)), "source_revision": build.REVISION, "trusted_seed_sha256": hashlib.sha256((reference.TRUSTED / "solution.json").read_bytes()).hexdigest(), "barrier_over_kBT_at_0p5K": record["barrier_meV"] / (0.08617333262 * 0.5), "reference_method": "One native state certifies both continued boundary saddles, full independent banded spectra/FD and both native descents. Full-size sparse HTST is calculated for the lower certified saddle only; both mechanisms also have N128 native dense/sparse checks. Total warm timing includes all steps.", "global_minimum_claim": "Lowest among compared native-certified mechanisms, not an exhaustive proof.", "time_limit_seconds": 90.0, "memory_limit_gib": 2.0, "peak_rss_kib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    destination = build.RATCHET / "private/challenge_pool/challenge" / identifier
    for target in [location, destination]:
        reference.write_json(target / "case.json", case)
        reference.write_json(target / "solution.json", solution)
        reference.write_json(target / "validation.json", validation)
    manifest_record = {"case_id": identifier, "family": family, "n_spins": count, "case_file": str((destination / "case.json").relative_to(build.RATCHET)), "solution_file": str((destination / "solution.json").relative_to(build.RATCHET)), "validation_file": str((destination / "validation.json").relative_to(build.RATCHET)), "reference_runtime_seconds": elapsed}
    reference.write_json(directory / "manifest_record.json", manifest_record)
    reference.write_json(directory / "extension_provenance.json", {"source_revision": build.REVISION, "generator_sha256": build.digest(__import__('pathlib').Path(__file__)), "base_generator_sha256": build.digest(build.ROOT / "build.py"), "reference_wrapper_sha256": build.digest(build.SIDECAR / "reference.py"), "case_sha256": build.digest(destination / "case.json"), "solution_sha256": build.digest(destination / "solution.json"), "validation_sha256": build.digest(destination / "validation.json"), "fresh_parameter_seed": seed, "parameter_perturbations": preparation["parameter_perturbations"]})
    print(f"CERTIFIED LARGE {identifier} runtime={elapsed:.3f}s native_sparse={stage['native_sparse_htst']:.3f}s RSS={validation['peak_rss_kib_process']}KiB", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=["boundary_localized", "soft_interface"])
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    if arguments.family == "boundary_localized":
        certify(arguments.family, 90544001, 3072)
    else:
        certify(arguments.family, 90544002, 4096)

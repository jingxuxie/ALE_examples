import argparse
import copy
import datetime
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RATCHET = ROOT.parents[1]
TASK = RATCHET.parents[2]
SIDECAR = TASK / "authoring/activation_scale_probe"
sys.path.insert(0, str(SIDECAR))
import reference
from spirit import chain, simulation, state, system
from spirit.parameters import gneb, llg

REVISION = "e82250d3b14411c2c2fa292d143f13e3e111ad8c"
ORIGINAL_BUILDER = reference.extended_case
SEED_DIRECTORIES = {
    "boundary_localized": "initial_domain_wall_01_731101",
    "soft_interface": "initial_exchange_spring_01_731201",
    "coherent_control": "initial_coherent_01_731001",
}
SPECS = {
    "initial": [("boundary_localized", 86421001, 1536), ("boundary_localized", 86421002, 2048), ("soft_interface", 86421003, 2048), ("soft_interface", 86421004, 2304), ("coherent_control", 86421005, 8), ("coherent_control", 86421006, 12)],
    "challenge": [("boundary_localized", 90312001, 1792), ("soft_interface", 90312002, 2176), ("coherent_control", 90312003, 11)],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def angles(spins):
    return np.arctan2(spins[:, 0], spins[:, 2])


def spins_from_angles(values):
    return np.column_stack((np.sin(values), np.zeros(len(values)), np.cos(values)))


def angular_deviation(saddle, minimum):
    difference = angles(saddle) - angles(minimum)
    return np.arctan2(np.sin(difference), np.cos(difference))


def parameters_for(seed):
    generator = np.random.default_rng(seed)
    return {"exchange_scale": float(generator.uniform(0.96, 1.04)), "easy_anisotropy_scale": float(generator.uniform(0.95, 1.05)), "transverse_field_scale": float(generator.uniform(0.96, 1.04)), "longitudinal_field_scale": float(generator.uniform(0.96, 1.04)), "boundary_easy_factor": float(generator.uniform(0.875, 0.915)), "interface_bond_perturbation": float(generator.uniform(-0.012, 0.012))}


def native_minima(case, directory):
    config = directory / "minimum_preparation.cfg"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(reference.spirit_config(case))
    with state.State(str(config), quiet=True) as pointer:
        chain.image_to_clipboard(pointer)
        chain.set_length(pointer, 2)
        for image, name in enumerate(["minimum_a", "minimum_b"]):
            reference.set_spins(pointer, np.asarray(case[name]), image)
            llg.set_convergence(pointer, 1e-11, idx_image=image)
            simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=30000, idx_image=image)
            case[name] = system.get_spin_directions(pointer, idx_image=image).copy().tolist()
            if reference.diagnose(case, np.asarray(case[name]), False)["residual_meV"] > 1e-8:
                raise RuntimeError("native endpoint preparation did not converge")


def prepared_case(family, seed, count, split, directory):
    started = time.perf_counter()
    reference.TRUSTED = reference.PRIVATE / "reference/initial" / SEED_DIRECTORIES[family]
    parameters = parameters_for(seed)
    if family == "coherent_control":
        case = load(reference.TRUSTED / "case.json")
        answer = load(reference.TRUSTED / "solution.json")
        case["n_spins"] = count
        case["exchange_meV"] = [case["exchange_meV"][0]] * (count - 1)
        case["anisotropy_meV"] = [case["anisotropy_meV"][0]] * count
        for name in ["minimum_a", "minimum_b"]:
            case[name] = [case[name][0]] * count
        original_saddle = np.tile(answer["saddle"][0], (count, 1))
    else:
        case, original_saddle = ORIGINAL_BUILDER(count)
    deviation = angular_deviation(original_saddle, np.asarray(case["minimum_a"]))
    case["case_id"] = f"ratchet1_{split}_{family}_{seed}"
    case["family"] = family
    case["seed"] = seed
    case["temperature_K"] = 0.5
    case["time_limit_seconds"] = 90.0
    exchange = np.asarray(case["exchange_meV"]) * parameters["exchange_scale"]
    tensors = np.asarray(case["anisotropy_meV"]).copy()
    tensors[:, 0, 0] *= parameters["easy_anisotropy_scale"]
    tensors[:, 2, 2] *= parameters["easy_anisotropy_scale"]
    if family == "boundary_localized":
        tensors[0, 2, 2] = tensors[-1, 2, 2] * parameters["boundary_easy_factor"]
    if family == "soft_interface":
        position = np.arange(count - 1)
        exchange *= 1 - parameters["interface_bond_perturbation"] * np.exp(-((position - 8) / 4)**2)
    case["exchange_meV"] = exchange.tolist()
    case["anisotropy_meV"] = tensors.tolist()
    case["field_meV"][0] *= parameters["transverse_field_scale"]
    case["field_meV"][2] *= parameters["longitudinal_field_scale"]
    native_minima(case, directory)
    saddle = spins_from_angles(angles(np.asarray(case["minimum_a"])) + deviation)
    return case, saddle, {"native_preparation_seconds": time.perf_counter() - started, "parameter_perturbations": parameters}


def native_branch(case, saddle_seed, directory):
    directory.mkdir(parents=True, exist_ok=True)
    reference.ROOT = directory
    reference.extended_case = lambda count: (copy.deepcopy(case), saddle_seed.copy())
    os.chdir(directory)
    started = time.perf_counter()
    reference.build(case["n_spins"])
    location = directory / f"N{case['n_spins']}"
    with np.load(location / "reference.npz", allow_pickle=False) as archive:
        solution = {name: archive[name].tolist() for name in archive.files}
    validation = load(location / "validation.json")
    validation["whole_branch_seconds"] = time.perf_counter() - started
    return solution, validation, location


def right_seed(case, family, selected_seed):
    minimum = np.asarray(case["minimum_a"])
    if family == "boundary_localized":
        deviation = angular_deviation(selected_seed, minimum)
    else:
        trusted = reference.PRIVATE / "reference/initial" / SEED_DIRECTORIES["boundary_localized"]
        trusted_case = load(trusted / "case.json")
        trusted_solution = load(trusted / "solution.json")
        small = angular_deviation(np.asarray(trusted_solution["saddle"]), np.asarray(trusted_case["minimum_a"]))
        deviation = np.zeros(case["n_spins"])
        deviation[:len(small)] = small
    return spins_from_angles(angles(minimum) + deviation[::-1])


def short_cold_paths(case, solution, directory):
    directory.mkdir(parents=True, exist_ok=True)
    config = directory / "spirit.cfg"
    config.write_text(reference.spirit_config(case))
    minimum_a = np.asarray(case["minimum_a"])
    minimum_b = np.asarray(case["minimum_b"])
    start = angles(minimum_a)
    difference = angular_deviation(minimum_b, minimum_a)
    tensors = np.asarray(case["anisotropy_meV"])
    width = float(np.sqrt(np.median(case["exchange_meV"]) / (2 * np.median(tensors[:, 2, 2]))))
    records = []
    for direction in [1, -1]:
        started = time.perf_counter()
        position = np.arange(case["n_spins"])
        if direction < 0:
            position = position[::-1]
        centers = np.linspace(-7 * width, case["n_spins"] - 1 + 7 * width, 21)
        fraction = (2 / np.pi) * np.arctan(np.exp((centers[:, None] - position) / width))
        path = [spins_from_angles(start + value * difference) for value in fraction]
        path[0], path[-1] = minimum_a, minimum_b
        with state.State(str(config), quiet=True) as pointer:
            chain.image_to_clipboard(pointer)
            chain.set_length(pointer, len(path))
            for image, spins in enumerate(path):
                reference.set_spins(pointer, spins, image)
            gneb.set_image_type_automatically(pointer)
            gneb.set_convergence(pointer, 1e-10)
            simulation.start(pointer, simulation.METHOD_GNEB, simulation.SOLVER_LBFGS_OSO, n_iterations=20000)
            energies = [float(reference.energy_gradient(case, system.get_spin_directions(pointer, idx_image=image))[0].sum()) for image in range(len(path))]
            peak = int(np.argmax(energies))
            saddle = system.get_spin_directions(pointer, idx_image=peak).copy()
        info = reference.diagnose(case, saddle)
        barrier = float(np.sum(reference.energy_gradient(case, saddle)[0] - reference.energy_gradient(case, minimum_a)[0]))
        valid = 0 < peak < len(path) - 1 and info["residual_meV"] < 2e-6 and info["eigenvalues"][0] < -1e-6 and info["eigenvalues"][1] > 1e-6
        record = {"direction": direction, "seconds": time.perf_counter() - started, "native_cold_path_validated": bool(valid), "peak_image": peak, "residual_meV": info["residual_meV"], "first_eigenvalues_meV": info["eigenvalues"][:3].tolist(), "barrier_meV": barrier, "barrier_difference_from_selected_meV": barrier - solution["barrier_meV"]}
        records.append(record)
        reference.write_json(directory / f"direction_{direction}.json", record)
        if not valid or abs(barrier - solution["barrier_meV"]) > 1e-4:
            raise RuntimeError(f"coherent control cold native path not certified: {record}")
    return records


def build_case(family, seed, count, split):
    started = time.perf_counter()
    identifier = f"ratchet1_{split}_{family}_{seed}"
    directory = ROOT / split / identifier
    directory.mkdir(parents=True, exist_ok=True)
    os.chdir(directory)
    print(f"BEGIN {identifier} N={count}", flush=True)
    dense_crosscheck = None
    if count > 128:
        small_case, small_seed, small_preparation = prepared_case(family, seed, 128, split, directory / "small_calibration")
        _, small_validation, small_location = native_branch(small_case, small_seed, directory / "small_calibration")
        dense_crosscheck = {"path": str((small_location / "validation.json").relative_to(RATCHET)), "native_dense": small_validation["dense_crosscheck"], "native_preparation": small_preparation}
    case, saddle_seed, preparation = prepared_case(family, seed, count, split, directory / "selected")
    solution, validation, location = native_branch(case, saddle_seed, directory / "selected")
    mechanisms = [{"mechanism": "warm_coherent" if family == "coherent_control" else "left_nucleation", "validated": True, "barrier_meV": solution["barrier_meV"], "validation_path": str((location / "validation.json").relative_to(RATCHET))}]
    if family != "coherent_control":
        alternative_seed = right_seed(case, family, saddle_seed)
        alternative_solution, alternative_validation, alternative_location = native_branch(case, alternative_seed, directory / "right_competitor")
        mechanisms.append({"mechanism": "right_nucleation", "validated": True, "barrier_meV": alternative_solution["barrier_meV"], "validation_path": str((alternative_location / "validation.json").relative_to(RATCHET)), "whole_branch_seconds": alternative_validation["whole_branch_seconds"]})
        if alternative_solution["barrier_meV"] < solution["barrier_meV"]:
            solution, validation, location = alternative_solution, alternative_validation, alternative_location
    else:
        mechanisms.extend({"mechanism": "cold_boundary_path", **record} for record in short_cold_paths(case, solution, directory / "cold_paths"))
    elapsed = time.perf_counter() - started
    if elapsed >= 90:
        raise RuntimeError(f"complete native preparation and comparison exceed90s: {elapsed}")
    validation.update({"reference_runtime_seconds": elapsed, "native_preparation": preparation, "same_parameter_small_dense_crosscheck": dense_crosscheck, "competing_mechanisms": mechanisms, "reference_method": "Warm native GNEB continuation with independently banded full tangent spectra, native HTST and native two-basin descents. Both boundary directions are compared for localized cases; coherent controls also have two cold21image native GNEB paths.", "global_minimum_claim": "Lowest among certified compared mechanisms, not an exhaustive proof over all spin configurations.", "case_id": identifier, "family": family, "seed": seed, "time_limit_seconds": 90.0, "memory_limit_gib": 2.0, "source_revision": REVISION, "parameter_perturbations": preparation["parameter_perturbations"], "selected_native_artifacts": str(location.relative_to(RATCHET)), "peak_rss_kib_build_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    destination = RATCHET / ("private/reference/initial" if split == "initial" else "private/challenge_pool/challenge") / identifier
    reference.write_json(destination / "case.json", case)
    reference.write_json(destination / "solution.json", solution)
    reference.write_json(destination / "validation.json", validation)
    print(f"CERTIFIED {identifier} runtime={elapsed:.3f}s barrier={solution['barrier_meV']:.9f}", flush=True)
    return {"case_id": identifier, "family": family, "n_spins": count, "case_file": str((destination / "case.json").relative_to(RATCHET)), "solution_file": str((destination / "solution.json").relative_to(RATCHET)), "validation_file": str((destination / "validation.json").relative_to(RATCHET)), "reference_runtime_seconds": elapsed}


def publish_manifest(split, records):
    destination = RATCHET / ("private/reference/initial" if split == "initial" else "private/challenge_pool/challenge")
    hashes = {record[name]: digest(RATCHET / record[name]) for record in records for name in ["case_file", "solution_file", "validation_file"]}
    manifest = {"source_revision": REVISION, "split": split, "seed_base": 86421001 if split == "initial" else 90312001, "cases": records, "sha256": hashes, "scope": "ratchet1 only; original frozen pilot is untouched", "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    reference.write_json(destination / "manifest.json", manifest)
    sources = [Path(__file__), SIDECAR / "reference.py", TASK / "pilots/activation/private/build_references.py", TASK / "authoring/spirit/core/python/spirit/libSpirit.so"]
    sources.extend(TASK / "authoring/spirit/core/src/engine" / name for name in ["Method_GNEB.cpp", "Hamiltonian_Heisenberg.cpp", "HTST.cpp", "Sparse_HTST.cpp"])
    reference.write_json(ROOT / f"{split}_provenance.json", {"source_revision": REVISION, "input_source_sha256": {str(path.relative_to(TASK)): digest(path) for path in sources}, "artifact_sha256": {str(path.relative_to(RATCHET)): digest(path) for path in sorted((ROOT / split).rglob("*")) if path.is_file()}, "manifest_sha256": digest(destination / "manifest.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["initial", "challenge"], required=True)
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    records = []
    for family, seed, count in SPECS[arguments.split]:
        records.append(build_case(family, seed, count, arguments.split))
        publish_manifest(arguments.split, records)

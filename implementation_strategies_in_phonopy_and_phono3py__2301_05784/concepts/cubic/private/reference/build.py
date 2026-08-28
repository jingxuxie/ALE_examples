"""Build private, source-grounded cubic interpolation cases and audit the oracle."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
PRIVATE = Path(__file__).resolve().parents[1]
ROOT = PRIVATE.parent
TARGET = ROOT.parents[1]
RUNTIME = TARGET / "author/runtime"
SOURCE = TARGET / "author/source"
sys.path.insert(0, str(RUNTIME))

import numpy as np
import phono3py
import phono3py._phono3py as extension
from phonopy.harmonic.dynamical_matrix import get_dynamical_matrix
from phonopy.physical_units import get_physical_units

from oracle import Oracle, runtime_versions


def import_file(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


weak = import_file("cubic_weak", ROOT / "participant/workspace/solve.py")
evaluator = import_file("cubic_evaluator", PRIVATE / "evaluator.py")
KEYS = evaluator.KEYS
DATASETS = {
    "NaCl": ["test/phono3py_params_NaCl222.yaml.xz"],
    "AlN": ["test/phono3py_params_AlN332.yaml.xz"],
    "Si": ["test/phono3py_si_pbesol.yaml", "test/FORCES_FC3_si_pbesol"],
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repository, *arguments):
    return subprocess.check_output(["git", "-C", str(repository), *arguments])


def relative_error(actual, expected):
    denominator = max(float(np.linalg.norm(expected)), np.finfo(float).tiny)
    return float(np.linalg.norm(actual - expected) / denominator)


def check_close(actual, expected, label, tolerance=2e-10):
    error = relative_error(actual, expected)
    if not np.isfinite(error) or error > tolerance:
        raise AssertionError(f"{label}: relative error {error} > {tolerance}")
    return error


def load_crystal(family):
    dataset = DATASETS[family]
    arguments = {}
    if len(dataset) == 2:
        arguments["forces_fc3_filename"] = SOURCE / "phono3py" / dataset[1]
    return phono3py.load(
        SOURCE / "phono3py" / dataset[0],
        is_nac=False, is_compact_fc=True, symmetrize_fc=True,
        fc_calculator="traditional", make_r0_average=True, **arguments,
    )


def full_force_constants(crystal):
    compact = crystal.fc3
    primitive = crystal.primitive
    permutations = primitive.atomic_permutations
    supercell_count = len(crystal.supercell)
    full = np.empty((supercell_count,) * 3 + (3,) * 3, dtype=np.float64)
    for superatom in range(supercell_count):
        representative = primitive.s2p_map[superatom]
        primitive_atom = primitive.p2p_map[representative]
        selected = permutations[permutations[:, superatom] == representative]
        if len(selected) != 1:
            raise ValueError("Expected exactly one translation to a representative")
        permutation = selected[0]
        full[superatom] = compact[primitive_atom][permutation[:, None], permutation[None, :]]
    return full


def geometry(crystal, force_constants=None):
    primitive = crystal.primitive
    vectors, multiplicities = primitive.get_smallest_vectors()
    return {
        "fc3": crystal.fc3 if force_constants is None else force_constants,
        "p2s_map": np.ascontiguousarray(primitive.p2s_map, dtype=np.int64),
        "s2p_map": np.ascontiguousarray(primitive.s2p_map, dtype=np.int64),
        "shortest_vectors": np.ascontiguousarray(vectors, dtype=np.float64),
        "multiplicities": np.ascontiguousarray(multiplicities, dtype=np.int64),
        "primitive_lattice": primitive.cell,
        "primitive_positions": primitive.scaled_positions,
        "supercell_lattice": crystal.supercell.cell,
        "supercell_positions": crystal.supercell.scaled_positions,
        "masses": primitive.masses,
    }


def sample_triplets(generator, count=10, denominator=1009):
    first_two = generator.integers(-450, 451, size=(2, 3))
    base = np.vstack((first_two, -first_two.sum(axis=0)))
    umklapp = base.copy()
    umklapp[2] += denominator * np.array([1, -1, 1])
    gamma = np.vstack((np.zeros(3, dtype=np.int64), first_two[0], -first_two[0]))
    addresses = [base, -base, base[[1, 2, 0]], base[[1, 0, 2]], umklapp, gamma]
    for index in range(count - len(addresses)):
        pair = generator.integers(-480, 481, size=(2, 3))
        reciprocal = generator.integers(-1, 2, size=3) if index % 2 else np.zeros(3, dtype=np.int64)
        addresses.append(np.vstack((pair, denominator * reciprocal - pair.sum(axis=0))))
    return np.array(addresses, dtype=np.float64) / denominator


def add_phonons(data, crystal, qpoints, generator, high_cutoff=False):
    dynamical_matrix = get_dynamical_matrix(
        crystal.fc2, crystal.phonon_supercell, crystal.phonon_primitive,
    )
    band_count = len(crystal.primitive) * 3
    frequencies = np.empty((len(qpoints), 3, band_count), dtype=np.float64)
    eigenvectors = np.empty((len(qpoints), 3, band_count, band_count), dtype=np.complex128)
    max_residual = 0.0
    max_unitarity = 0.0
    for triplet_index, triplet in enumerate(qpoints):
        for leg, wavevector in enumerate(triplet):
            dynamical_matrix.run(wavevector)
            matrix = dynamical_matrix.dynamical_matrix
            values, modes = np.linalg.eigh(matrix)
            modes *= np.exp(2j * np.pi * generator.random(band_count))[None, :]
            max_residual = max(max_residual, relative_error(matrix @ modes, modes * values))
            max_unitarity = max(max_unitarity, relative_error(modes.conj().T @ modes, np.eye(band_count)))
            frequencies[triplet_index, leg] = (
                np.sign(values) * np.sqrt(np.abs(values)) * get_physical_units().DefaultToTHz
            )
            eigenvectors[triplet_index, leg] = modes
    cutoff = float(frequencies[0, 1, band_count // 3]) if high_cutoff else 0.01
    if cutoff <= 0:
        raise ValueError("Expected a positive cutoff")
    data.update(qpoints=qpoints, frequencies=frequencies, eigenvectors=eigenvectors,
                cutoff_frequency=np.array(cutoff, dtype=np.float64))
    return {"eigenpair_relative_residual": max_residual, "eigenvector_unitarity_error": max_unitarity,
            "frequency_min_THz": float(frequencies.min()), "frequency_max_THz": float(frequencies.max()),
            "cutoff_frequency_THz": cutoff, "frequencies_equal_to_cutoff": int(np.sum(frequencies == cutoff))}


def monolithic_interaction(data, average, all_shortest, denominator=1009):
    primitive_count = len(data["p2s_map"])
    band_count = primitive_count * 3
    triplet_count = len(data["qpoints"])
    addresses = np.rint(data["qpoints"].reshape(-1, 3) * denominator).astype(np.int64)
    check_close(addresses / denominator, data["qpoints"].reshape(-1, 3), "integer grid encoding")
    strengths = np.zeros((triplet_count,) + (band_count,) * 3, dtype=np.float64)
    force_constants = np.ascontiguousarray(data["fc3"])
    extension.interaction(
        strengths, np.zeros(strengths.shape, dtype=np.int8),
        np.ascontiguousarray(data["frequencies"].reshape(-1, band_count)),
        np.ascontiguousarray(data["eigenvectors"].reshape(-1, band_count, band_count)),
        np.arange(triplet_count * 3, dtype=np.int64).reshape(-1, 3),
        addresses, np.full(3, denominator, dtype=np.int64), np.eye(3, dtype=np.int64),
        force_constants, np.ones(force_constants.shape[:3], dtype=np.int8),
        np.ascontiguousarray(data["shortest_vectors"]), np.ascontiguousarray(data["multiplicities"]),
        np.ascontiguousarray(data["masses"]), np.ascontiguousarray(data["p2s_map"]),
        np.ascontiguousarray(data["s2p_map"]), np.arange(band_count, dtype=np.int64),
        0, int(average), np.ascontiguousarray(all_shortest, dtype=np.int8),
        float(data["cutoff_frequency"]), 1,
    )
    return strengths


def verify_high_level_api(crystal, oracle):
    results = {}
    reports = {}
    optimized_mask = None
    for average in (False, True):
        model = phono3py.Phono3py(
            crystal.unitcell, crystal.supercell_matrix, primitive_matrix=crystal.primitive_matrix,
            make_r0_average=average, cutoff_frequency=0.01,
        )
        model.fc2 = crystal.fc2
        model.fc3 = crystal.fc3
        model.mesh_numbers = [5, 5, 5]
        model.init_phph_interaction()
        interaction = model.phph_interaction
        if interaction.make_r0_average != average:
            raise AssertionError("Constructor flag did not reach Interaction")
        interaction.run_phonon_solver()
        interaction.set_grid_point(1)
        interaction.run(lang="C")
        triplets = interaction.get_triplets_at_q()[0]
        frequencies, eigenvectors, _ = interaction.get_phonons()
        qpoints = model.grid.addresses[triplets] @ model.grid.QDinv.T
        data = geometry(model)
        data.update(qpoints=qpoints, frequencies=frequencies[triplets],
                    eigenvectors=eigenvectors[triplets], cutoff_frequency=np.array(0.01))
        direct = oracle.solve(data, average=average)
        raw = interaction.interaction_strength / interaction.unit_conversion_factor
        reports[str(average)] = {
            "api_flag": interaction.make_r0_average,
            "triplets": len(triplets),
            "tensor_contraction_vs_high_level_C": check_close(
                direct["coupling_strength"], raw, f"API {average} vs direct C"),
            "strength_norm": float(np.linalg.norm(raw)),
            "unit_conversion_removed": float(interaction.unit_conversion_factor),
        }
        results[average] = raw.copy()
        optimized_mask = interaction.all_shortest.copy()
    difference = relative_error(results[False], results[True])
    if difference < 1e-5:
        raise AssertionError(f"No meaningful explicit-API on/off distinction: {difference}")
    reports["on_off_relative_difference"] = difference
    return reports, optimized_mask


def subset(data, count=2):
    return {key: value[:count].copy() if key in ("qpoints", "frequencies", "eigenvectors") else value
            for key, value in data.items()}


def validate_case(data, reference, baseline, oracle, all_shortest):
    report = {}
    legacy = oracle.solve(data, average=False)
    for key in KEYS:
        report[f"baseline_vs_C_off_{key}"] = check_close(baseline[key], legacy[key], f"C-off {key}")
        report[f"weak_error_{key}"] = evaluator.component_error(baseline[key], reference[key])
        if report[f"weak_error_{key}"] < 1e-5:
            raise AssertionError(f"Uninformative weak error for {key}")
    optimized = oracle.solve(data, all_shortest=all_shortest)
    for key in KEYS:
        report[f"all_shortest_optimization_{key}"] = check_close(
            optimized[key], reference[key], f"all-shortest {key}")
    for average, expected in ((False, legacy), (True, reference)):
        combined = monolithic_interaction(data, average, all_shortest)
        report[f"monolithic_C_interaction_{average}"] = check_close(
            combined, expected["coupling_strength"], f"monolithic {average}")
    small = subset(data)
    small_reference = {key: value[:2] for key, value in reference.items()}
    tensor = small_reference["reciprocal_fc3"]
    strength = small_reference["coupling_strength"]
    literal = []
    contracted = []
    for index, triplet in enumerate(small["qpoints"]):
        average = (
            weak.single_origin(small, triplet)
            + weak.single_origin(small, triplet[[1, 0, 2]]).transpose(1, 0, 2, 4, 3, 5)
            + weak.single_origin(small, triplet[[2, 1, 0]]).transpose(2, 1, 0, 5, 4, 3)
        ) / 3
        literal.append(average)
        contracted.append(weak.contract_modes(
            tensor[index], small["eigenvectors"][index], small["frequencies"][index],
            small["masses"], float(small["cutoff_frequency"])))
    report["C_tensor_vs_literal_contract"] = check_close(np.array(literal), tensor, "literal average")
    report["C_contraction_vs_numpy"] = check_close(np.array(contracted), strength, "NumPy contraction")
    reversed_data = dict(small, qpoints=-small["qpoints"], eigenvectors=small["eigenvectors"].conj())
    reversed_result = oracle.solve(reversed_data)
    report["time_reversal_tensor"] = check_close(reversed_result["reciprocal_fc3"], tensor.conj(), "conjugation")
    report["time_reversal_strength"] = check_close(reversed_result["coupling_strength"], strength, "time reversal")
    for permutation in ((1, 0, 2), (1, 2, 0)):
        permuted = dict(small)
        for key in ("qpoints", "frequencies", "eigenvectors"):
            permuted[key] = small[key][:, permutation].copy()
        changed = oracle.solve(permuted)
        tensor_axes = (0,) + tuple(1 + index for index in permutation) + tuple(4 + index for index in permutation)
        strength_axes = (0,) + tuple(1 + index for index in permutation)
        report[f"leg_permutation_tensor_{permutation}"] = check_close(
            changed["reciprocal_fc3"], tensor.transpose(tensor_axes), "tensor leg permutation")
        report[f"leg_permutation_strength_{permutation}"] = check_close(
            changed["coupling_strength"], strength.transpose(strength_axes), "mode leg permutation")
    gauge = np.exp(1j * np.linspace(0.17, 2.73, small["eigenvectors"].shape[-1]))
    gauged = oracle.solve(dict(small, eigenvectors=small["eigenvectors"] * gauge))
    report["eigenvector_phase_invariance"] = check_close(gauged["coupling_strength"], strength, "phase gauge")
    mass_scaled = oracle.solve(dict(small, masses=small["masses"] * 2))
    report["mass_scaling"] = check_close(mass_scaled["coupling_strength"], strength / 8, "mass scaling")
    scaled = oracle.solve(dict(small, fc3=small["fc3"] * 1.7))
    report["fc3_tensor_scaling"] = check_close(scaled["reciprocal_fc3"], tensor * 1.7, "fc3 scaling")
    report["fc3_strength_scaling"] = check_close(scaled["coupling_strength"], strength * 1.7**2, "strength scaling")
    shifted = dict(small, qpoints=small["qpoints"].copy(), eigenvectors=small["eigenvectors"].copy())
    reciprocal_shift = np.array([1, -1, 0])
    shifted["qpoints"][:, 0] += reciprocal_shift
    shifted["qpoints"][:, 2] -= reciprocal_shift
    phase = np.exp(2j * np.pi * (small["primitive_positions"] @ reciprocal_shift))
    shifted["eigenvectors"][:, 0] *= np.repeat(phase.conj(), 3)[None, :, None]
    shifted["eigenvectors"][:, 2] *= np.repeat(phase, 3)[None, :, None]
    shifted_result = oracle.solve(shifted)
    tensor_phase = (phase[:, None, None] * phase.conj()[None, None, :])[None, ..., None, None, None]
    report["reciprocal_gauge_tensor"] = check_close(shifted_result["reciprocal_fc3"], tensor * tensor_phase, "reciprocal gauge tensor")
    report["reciprocal_gauge_strength"] = check_close(shifted_result["coupling_strength"], strength, "reciprocal gauge strength")
    frequencies = data["frequencies"]
    cutoff = float(data["cutoff_frequency"])
    mask = ((frequencies[:, 0, :, None, None] > cutoff)
            & (frequencies[:, 1, None, :, None] > cutoff)
            & (frequencies[:, 2, None, None, :] > cutoff))
    if np.any(reference["coupling_strength"][~mask] != 0):
        raise AssertionError("C frequency mask mismatch")
    report["masked_mode_triples"] = int(np.sum(~mask))
    report["active_mode_triples"] = int(np.sum(mask))
    edge = subset(data, 1)
    edge["frequencies"] = edge["frequencies"].copy()
    edge["frequencies"][0, 0, :3] = [-0.5, 0.0, cutoff]
    edge_result = oracle.solve(edge)
    if np.any(edge_result["coupling_strength"][0, :3] != 0):
        raise AssertionError("Negative/zero/equal cutoff frequency incorrectly included")
    report["strict_cutoff_edge_test"] = True
    return report


def measure_cli(script, input_path, output_path, log_prefix, private_runtime=False):
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    environment["PYTHONPATH"] = str(RUNTIME) if private_runtime else ""
    log_prefix.parent.mkdir(parents=True, exist_ok=True)
    rss_path = Path(f"{log_prefix}.rss.txt")
    command = ["/usr/bin/time", "-f", "%M", "-o", str(rss_path),
               sys.executable, "-B", str(script), str(input_path), str(output_path)]
    started = time.perf_counter()
    completed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=180)
    elapsed = time.perf_counter() - started
    Path(f"{log_prefix}.stdout.txt").write_text(completed.stdout)
    Path(f"{log_prefix}.stderr.txt").write_text(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"CLI {script} failed: {completed.stderr}")
    return {"status": "ok", "seconds": elapsed, "max_rss_kb": int(rss_path.read_text().strip()),
            "command": command, "measurement": "trusted direct CLI; sandbox evaluation reported separately"}


def validate_scoring(reference, baseline, case, data):
    curve = []
    for factor in (0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 10.0):
        actual = {key: reference[key] + factor * (baseline[key] - reference[key]) for key in KEYS}
        scores = evaluator.score_case(actual, reference, baseline, case, data)
        tensor_expected = 1 / (1 + factor)
        if abs(scores["reciprocal_fc3"] - tensor_expected) > 1e-10:
            raise AssertionError("Scoring curve is not continuous relative to measured weak error")
        curve.append({"error_multiple": factor, "scores": scores})
    broken = dict(reference, reciprocal_fc3=np.full_like(reference["reciprocal_fc3"], np.nan))
    scores = evaluator.score_case(broken, reference, baseline, case, data)
    if scores != {"reciprocal_fc3": 0.0, "coupling_strength": 1.0}:
        raise AssertionError("Component isolation or nonfinite rejection failed")
    return curve


def provenance():
    result = {"runtime_versions": runtime_versions(), "python": sys.version,
              "platform": platform.platform(), "kernel": str(extension.__file__),
              "kernel_sha256": sha256(extension.__file__), "sources": {}, "datasets": {},
              "threads": {key: os.environ[key] for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}}
    revisions = {"phono3py": "v3.19.2", "phonopy": "v2.43.4"}
    files = {
        "phono3py": ["c/real_to_reciprocal.c", "c/real_to_reciprocal.h", "c/reciprocal_to_normal.c",
                     "c/reciprocal_to_normal.h", "c/interaction.c", "c/_phono3py.cpp",
                     "phono3py/phonon3/interaction.py", "phono3py/api_phono3py.py"],
        "phonopy": ["phonopy/structure/cells.py", "phonopy/harmonic/dynamical_matrix.py",
                    "phonopy/harmonic/force_constants.py"],
    }
    for name, revision in revisions.items():
        repository = SOURCE / name
        result["sources"][name] = {
            "checkout_commit": git(repository, "rev-parse", "HEAD").decode().strip(),
            "runtime_release_tag": revision,
            "runtime_release_commit": git(repository, "rev-parse", f"{revision}^{{commit}}").decode().strip(),
            "files": files[name],
            "checkout_file_sha256": {filename: sha256(repository / filename) for filename in files[name]},
        }
    for family, filenames in DATASETS.items():
        result["datasets"][family] = [{"repository": "phono3py", "path": filename,
                                         "sha256": sha256(SOURCE / "phono3py" / filename)} for filename in filenames]
    result["pinned_C_source"] = {
        "repository": "phonopy/phono3py", "commit": "5a4fd11f713ee1457fe4eabea84f1dfa89a685df",
        "path": "c/real_to_reciprocal.c", "local": "reference/real_to_reciprocal-3.19.2.c",
        "sha256": sha256(PRIVATE / "reference/real_to_reciprocal-3.19.2.c"),
    }
    result["dependencies"] = {"oracle": ["numpy==2.2.6", "phono3py==3.19.2", "phonopy==2.43.4", "spglib==2.5.0",
                                          "scipy==1.15.3", "h5py==3.16.0", "PyYAML==6.0.3"],
                              "participant": ["Python >=3.10", "NumPy >=1.21"],
                              "measurement": ["GNU time"], "evaluation": ["bubblewrap", "author/evaluation.py"]}
    return result


def build_case(crystal, family, layout, split, seed, index, oracle, full, all_shortest):
    case_id = f"{split}-{seed}-{family.lower()}-{layout}"
    generator = np.random.default_rng(np.random.SeedSequence([seed, index, 0 if layout == "compact" else 1]))
    data = geometry(crystal, None if layout == "compact" else full)
    phonon_report = add_phonons(data, crystal, sample_triplets(generator), generator, high_cutoff=layout == "full")
    input_path = PRIVATE / "challenge_pool" / f"{case_id}.input.npz"
    reference_path = PRIVATE / "reference/outputs" / f"{case_id}.reference.npz"
    baseline_path = PRIVATE / "reference/outputs" / f"{case_id}.baseline.npz"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(input_path, **data)
    reference_run = measure_cli(PRIVATE / "reference/solve.py", input_path, reference_path,
                                PRIVATE / "reference/measurements" / f"{case_id}.reference", private_runtime=True)
    baseline_run = measure_cli(ROOT / "participant/workspace/solve.py", input_path, baseline_path,
                               PRIVATE / "reference/measurements" / f"{case_id}.baseline")
    reference = evaluator.load_archive(reference_path)
    baseline = evaluator.load_archive(baseline_path)
    validation = validate_case(data, reference, baseline, oracle, all_shortest)
    compact_data = dict(data, fc3=crystal.fc3)
    full_data = dict(data, fc3=full)
    compact_result = oracle.solve(subset(compact_data))
    full_result = oracle.solve(subset(full_data))
    for key in KEYS:
        validation[f"compact_full_{key}"] = check_close(compact_result[key], full_result[key], f"compact/full {key}")
    case = {"id": case_id, "family": family, "split": split,
            "input": str(input_path.relative_to(PRIVATE)), "reference": str(reference_path.relative_to(PRIVATE)),
            "baseline": str(baseline_path.relative_to(PRIVATE)), "timeout": 180, "memory_mb": 8192,
            "keys": list(KEYS), "seed": seed, "layout": layout,
            "primitive_atoms": len(crystal.primitive), "supercell_atoms": len(crystal.supercell),
            "triplets": len(data["qpoints"]), "input_sha256": sha256(input_path),
            "reference_sha256": sha256(reference_path), "baseline_sha256": sha256(baseline_path),
            "weak_errors": {key: validation[f"weak_error_{key}"] for key in KEYS}}
    case["baseline_scores"] = evaluator.score_case(baseline, reference, baseline, case, data)
    case["reference_scores"] = evaluator.score_case(reference, reference, baseline, case, data)
    supercell_in_primitive = data["supercell_lattice"] @ np.linalg.inv(data["primitive_lattice"])
    commensurate = data["qpoints"] @ supercell_in_primitive.T
    report = {"id": case_id, "phonons": phonon_report, "validation": validation,
              "reference_run": reference_run, "baseline_run": baseline_run,
              "noncommensurate_wavevectors": int(np.sum(np.any(np.abs(commensurate - np.rint(commensurate)) > 1e-8, axis=-1))),
              "umklapp_triplets": int(np.sum(np.any(np.rint(data["qpoints"].sum(axis=1)) != 0, axis=-1))),
              "maximum_shortest_vector_multiplicity": int(data["multiplicities"][..., 0].max()),
              "tied_shortest_vector_pairs": int(np.sum(data["multiplicities"][..., 0] > 1)),
              "scoring_curve": validate_scoring(reference, baseline, case, data)}
    print(json.dumps({"built": case_id, "weak_errors": case["weak_errors"],
                      "baseline_seconds": baseline_run["seconds"]}), flush=True)
    return case, report


def build_smoke(crystal):
    generator = np.random.default_rng(31922)
    data = geometry(crystal)
    add_phonons(data, crystal, sample_triplets(generator)[:1], generator)
    destination = ROOT / "participant/input/smoke.npz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("all", "pool", "heldout"), default="all")
    parser.add_argument("--pool-seed", type=int, default=730201)
    parser.add_argument("--heldout-seed", type=int, default=918427)
    parser.add_argument("--manifest", default="challenge_pool/manifest.json", help="Path relative to private/")
    arguments = parser.parse_args()
    manifest_path = (PRIVATE / arguments.manifest).resolve()
    if not manifest_path.is_relative_to(PRIVATE):
        raise ValueError("Manifest must remain inside this pilot's private directory")
    if arguments.pool_seed == arguments.heldout_seed:
        raise ValueError("Pool and heldout seeds must be independent")
    started = time.perf_counter()
    oracle = Oracle()
    records = []
    reports = []
    metadata = provenance()
    metadata["api_validation"] = {}
    metadata["force_constants"] = {}
    splits = ("pool", "heldout") if arguments.split == "all" else (arguments.split,)
    for index, family in enumerate(DATASETS):
        print(f"Loading official {family} data", flush=True)
        crystal = load_crystal(family)
        full = full_force_constants(crystal)
        fc_report = {
            "compact_shape": list(crystal.fc3.shape), "full_shape": list(full.shape),
            "second_first_permutation_error": check_close(full.transpose(1, 0, 2, 4, 3, 5), full, f"{family} FC permutation"),
            "third_first_permutation_error": check_close(full.transpose(2, 1, 0, 5, 4, 3), full, f"{family} FC permutation"),
            "compact_representative_rows": check_close(full[crystal.primitive.p2s_map], crystal.fc3, "full representative rows"),
            "primitive_atoms": len(crystal.primitive), "supercell_atoms": len(crystal.supercell),
            "p2s_map": crystal.primitive.p2s_map.tolist(), "nac": False,
            "fc_solver": "traditional", "symmetrize_fc": True,
        }
        metadata["force_constants"][family] = fc_report
        api_report, all_shortest = verify_high_level_api(crystal, oracle)
        metadata["api_validation"][family] = api_report
        print(f"{family}: verified explicit API gap {api_report['on_off_relative_difference']:.6g}", flush=True)
        for split in splits:
            seed = arguments.pool_seed if split == "pool" else arguments.heldout_seed
            for layout in ("compact", "full"):
                record, report = build_case(crystal, family, layout, split, seed, index, oracle, full, all_shortest)
                records.append(record)
                reports.append(report)
        if family == "Si" and arguments.split == "all":
            build_smoke(crystal)
        del full, crystal
    input_hashes = [case["input_sha256"] for case in records]
    if len(set(input_hashes)) != len(input_hashes):
        raise AssertionError("Duplicate inputs across splits")
    metadata["build_seconds"] = time.perf_counter() - started
    metadata["build_max_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metadata["case_count"] = len(records)
    metadata["pool_seed"] = arguments.pool_seed
    metadata["heldout_seed"] = arguments.heldout_seed
    metadata["split"] = arguments.split
    metadata["cases"] = reports
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(records, indent=2) + "\n")
    audit_path = PRIVATE / "reference" / f"{manifest_path.stem}.audit.json"
    audit_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "audit": str(audit_path),
                      "seconds": metadata["build_seconds"], "cases": len(records)}), flush=True)


if __name__ == "__main__":
    main()

"""Export pinned real polar fixtures and measure independent solution branches."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time


REFERENCE = Path(__file__).resolve().parent
PRIVATE = REFERENCE.parent
POLAR = PRIVATE.parent
TARGET = POLAR.parents[1]
RUNTIME = TARGET / "author/runtime4"
SOURCE = TARGET / "author/source/phonopy"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(PRIVATE))
os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
sys.dont_write_bytecode = True

import numpy as np
import phonopy
from phonopy.harmonic.derivative_dynmat import DerivativeOfDynamicalMatrix
from phonopy.phonon.group_velocity import GroupVelocity

from evaluator import errors, score_details


DEFAULT_SEED = 230105784
REQUIRED = ("derivative", "response", "velocity", "branch_velocity")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(SOURCE), *arguments])


def material(name):
    folder = REFERENCE / "fixtures" / name
    folder.mkdir(parents=True, exist_ok=True)
    names = [f"phonopy_disp_{name}.yaml", f"FORCE_SETS_{name}", f"BORN_{name}"]
    for filename in names:
        (folder / filename).write_bytes(git("show", f"v4.1.0:test/{filename}"))
    phonon = phonopy.load(
        folder / names[0], force_sets_filename=folder / names[1], born_filename=folder / names[2],
        fc_calculator="traditional", is_compact_fc=False, lang="Rust", symmetrize_fc=True,
    )
    dm = phonon.dynamical_matrix
    dm.make_Gonze_nac_dataset()
    vectors, rows, columns, blocks = [], [], [], []
    representative = {int(value): index for index, value in enumerate(dm._p2s_map)}
    for row in range(len(phonon.primitive)):
        for super_atom in range(len(phonon.supercell)):
            column = representative[int(dm._s2p_map[super_atom])]
            count, start = dm._multi[super_atom, row]
            block = dm.short_range_force_constants[dm._p2s_map[row], super_atom]
            block = block / np.sqrt(phonon.primitive.masses[row] * phonon.primitive.masses[column]) / count
            for vector in dm._svecs[start:start + count]:
                vectors.append(vector @ phonon.primitive.cell)
                rows.append(row)
                columns.append(column)
                blocks.append(block)
    data = {
        "schema_version": np.int64(1), "cell": phonon.primitive.cell.copy(),
        "positions": phonon.primitive.positions.copy(), "masses": phonon.primitive.masses.copy(),
        "born": dm.born.copy(), "dielectric": dm.dielectric_constant.copy(),
        "nac_factor": np.float64(dm.nac_factor), "ewald_lambda": np.float64(dm._Lambda),
        "g_vectors": dm._G_list.copy(), "sr_vectors": np.array(vectors),
        "sr_i": np.array(rows, dtype=np.int64), "sr_j": np.array(columns, dtype=np.int64),
        "sr_blocks": np.array(blocks), "frequency_factor": np.float64(phonon.unit_conversion_factor),
        "branch_tolerance": np.float64(1e-8),
    }
    return phonon, data, {f"test/{filename}": digest(folder / filename) for filename in names}


def rotation_from_rng(rng):
    rotation, diagonal = np.linalg.qr(rng.normal(size=(3, 3)))
    rotation *= np.sign(np.diag(diagonal))[None, :]
    rotation[:, -1] *= np.linalg.det(rotation)
    return rotation


def transform_derivatives(values, rotation, atoms):
    cartesian_rotation = np.kron(np.eye(atoms), rotation)
    transformed = cartesian_rotation @ values @ cartesian_rotation.T
    return np.einsum("ab,qbij->qaij", rotation, transformed)


def classify(eigenvalues, factor):
    frequencies = np.sign(eigenvalues) * np.sqrt(np.abs(eigenvalues)) * factor
    groups = np.zeros(len(frequencies), dtype=np.int64)
    for index in range(1, len(groups)):
        groups[index] = groups[index - 1] + int(abs(frequencies[index] - frequencies[index - 1]) > 1e-7)
    return groups, frequencies > 0.05


def response_reference(data, cartesian):
    response = np.zeros_like(cartesian)
    packets, _, modes, _ = response.shape
    velocity = np.zeros((packets, len(data["response_directions"]), modes))
    branch_velocity = np.zeros((packets, len(data["response_directions"]), modes, 3))
    off_diagonal_energy = 0.0
    for packet in range(packets):
        for label in np.unique(data["response_groups"][packet]):
            indices = np.flatnonzero(data["response_groups"][packet] == label)
            if not data["response_active"][packet, indices[0]]:
                continue
            basis = data["response_eigenvectors"][packet][:, indices]
            scale = float(data["frequency_factor"]) / (2 * np.sqrt(data["response_eigenvalues"][packet, indices].mean()))
            for axis in range(3):
                for row, mode_row in enumerate(indices):
                    for column, mode_column in enumerate(indices):
                        value = scale * np.vdot(basis[:, row], cartesian[packet, axis] @ basis[:, column])
                        response[packet, axis, mode_row, mode_column] = value
                        if row != column:
                            off_diagonal_energy += abs(value) ** 2
            for direction, vector in enumerate(data["response_directions"]):
                directional = np.einsum("m,mij->ij", vector, cartesian[packet])
                official = GroupVelocity._perturb_D(None, [directional, directional, *cartesian[packet]], basis) * scale
                ordering = np.argsort(official[:, 0])
                slopes = official[ordering, 0]
                values = official[ordering, 1:]
                boundaries = np.flatnonzero(np.diff(slopes) > float(data["branch_tolerance"])) + 1
                for cluster in np.split(np.arange(len(indices)), boundaries):
                    values[cluster] = values[cluster].mean(axis=0)
                velocity[packet, direction, indices] = slopes
                branch_velocity[packet, direction, indices] = values
    return response, velocity, branch_velocity, float(np.sqrt(off_diagonal_energy))


def make_case(phonon, base, rng, batch, oblique, near_gamma):
    data = {key: np.array(value, copy=True) for key, value in base.items()}
    atoms = len(data["masses"])
    directions = rng.normal(size=(batch, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    lengths = rng.uniform(0.025, 0.13, size=batch)
    if near_gamma:
        near_count = 3 * batch // 4
        lengths[:near_count] = np.geomspace(2.2e-5, 2e-3, near_count) * rng.uniform(1, 1.15, near_count)
    queries = directions * lengths[:, None]
    ddm = DerivativeOfDynamicalMatrix(phonon.dynamical_matrix, lang="Rust")
    official, backend_errors = [], []
    for index, wavevector in enumerate(queries):
        reduced = wavevector @ base["cell"].T
        ddm.run(reduced)
        expected = ddm.d_dynamical_matrix.copy()
        if index in (0, batch // 2, batch - 1):
            ddm.run(reduced, force_python=True)
            backend_errors.append(float(np.linalg.norm(expected - ddm.d_dynamical_matrix) / max(np.linalg.norm(expected), 1e-10)))
        official.append(expected)
    rotation = rotation_from_rng(rng) if oblique else np.eye(3)
    basis_change = np.array([[1, 1, 0], [0, 1, 1], [0, 0, 1]]) if oblique else np.eye(3)
    data["cell"] = basis_change @ base["cell"] @ rotation.T
    for key in ("positions", "g_vectors", "sr_vectors"):
        data[key] = base[key] @ rotation.T
    data["born"] = rotation @ base["born"] @ rotation.T
    data["dielectric"] = rotation @ base["dielectric"] @ rotation.T
    data["sr_blocks"] = rotation @ base["sr_blocks"] @ rotation.T
    data["q_cart"] = queries @ rotation.T
    expected_derivative = transform_derivatives(np.array(official), rotation, atoms)
    response_points = [[0.13, 0.13, 0.13], [0.27, 0.27, 0.27], [0.19, 0, 0], [0, 0, 0.17],
                       [0.5, 0, 0], [0.5, 0.5, 0], [0.25, 0.25, 0], [0.5, 0.25, 0.25]]
    for _ in range(8 if batch < 80 else 16):
        scale = rng.uniform(0.03, 0.4)
        response_points.extend([[scale, scale, scale], [0, 0, scale]])
    matrices, values, eigenvectors, labels, active = [], [], [], [], []
    unitary_cartesian = np.kron(np.eye(atoms), rotation)
    for reduced in response_points:
        phonon.dynamical_matrix.run(reduced)
        eigenvalues, basis = np.linalg.eigh(phonon.dynamical_matrix.dynamical_matrix)
        groups, usable = classify(eigenvalues, float(data["frequency_factor"]))
        basis = unitary_cartesian @ basis
        for label in np.unique(groups):
            indices = np.flatnonzero(groups == label)
            random_matrix = rng.normal(size=(len(indices), len(indices))) + 1j * rng.normal(size=(len(indices), len(indices)))
            gauge, _ = np.linalg.qr(random_matrix)
            basis[:, indices] = basis[:, indices] @ gauge
            usable[indices] = np.all(usable[indices])
        ddm.run(reduced)
        matrices.append(ddm.d_dynamical_matrix.copy())
        values.append(eigenvalues)
        eigenvectors.append(basis)
        labels.append(groups)
        active.append(usable)
    cartesian = transform_derivatives(np.array(matrices), rotation, atoms)
    data["response_ddm_reduced"] = np.einsum("am,pmij->paij", np.linalg.inv(data["cell"].T), cartesian)
    data["response_eigenvalues"] = np.array(values)
    data["response_eigenvectors"] = np.array(eigenvectors)
    data["response_groups"] = np.array(labels)
    data["response_active"] = np.array(active)
    extra_directions = rng.normal(size=(2, 3))
    extra_directions /= np.linalg.norm(extra_directions, axis=1)[:, None]
    data["response_directions"] = np.concatenate([np.eye(3), extra_directions])
    response, velocity, branch_velocity, mixing = response_reference(data, cartesian)
    minimum_distance = float(np.min(np.linalg.norm(data["q_cart"][:, None] + data["g_vectors"][None, :], axis=2)))
    if minimum_distance < 2e-5:
        raise ValueError("query entered the upstream Gamma guard")
    degenerate_groups = sum(np.count_nonzero(np.bincount(group) > 1) for group in labels)
    audit = {"rust_python_max_relative_error": max(backend_errors), "minimum_reciprocal_distance": minimum_distance,
             "degenerate_groups": int(degenerate_groups), "subspace_off_diagonal_norm": mixing,
             "derivative_queries": batch, "response_packets": len(values), "atoms": atoms,
             "reciprocal_vectors": len(data["g_vectors"]), "short_range_terms": len(data["sr_vectors"])}
    return data, {"derivative": expected_derivative, "response": response, "velocity": velocity,
                  "branch_velocity": branch_velocity}, audit


def execute(solver, input_path, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    measurements = output_path.with_suffix(".time")
    environment = dict(os.environ, PYTHONPATH=str(RUNTIME), OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    started = time.perf_counter()
    process = subprocess.run(
        ["/usr/bin/time", "-f", "%e %M", "-o", str(measurements), sys.executable, str(solver), str(input_path), str(output_path)],
        env=environment, capture_output=True, text=True, timeout=180, cwd=output_path.parent,
    )
    if process.returncode:
        raise RuntimeError(f"{solver}: {process.stderr}")
    seconds, rss = measurements.read_text().split()
    with np.load(output_path, allow_pickle=False) as archive:
        diagnostics = {key: float(archive[key]) for key in archive.files if key not in REQUIRED}
    return {"seconds": time.perf_counter() - started, "timed_seconds": float(seconds), "max_rss_kb": int(rss),
            "branch_diagnostics": diagnostics, "status": "ok", "stdout": process.stdout, "stderr": process.stderr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--fresh-heldout", action="store_true")
    parser.add_argument("--no-measure", action="store_true")
    args = parser.parse_args()
    if phonopy.__version__ != "4.1.0":
        raise RuntimeError(f"expected phonopy 4.1.0, got {phonopy.__version__}")
    pool = PRIVATE / "challenge_pool"
    if args.fresh_heldout:
        pool /= f"fresh_{args.seed}"
        if args.seed == DEFAULT_SEED:
            parser.error("fresh heldout requires a different seed")
    output_group = f"fresh_{args.seed}" if args.fresh_heldout else "initial"
    pool.mkdir(parents=True, exist_ok=True)
    (POLAR / "private/reference/author_measurements").mkdir(parents=True, exist_ok=True)
    manifest, reports, fixture_hashes = [], [], {}
    baseline = POLAR / "participant/workspace/solve.py"
    for family_index, family in enumerate(("NaCl", "SnO2", "TiO2")):
        phonon, base, hashes = material(family)
        fixture_hashes.update(hashes)
        for split_index, split in enumerate(("pool", "heldout")):
            if args.fresh_heldout and split != "heldout":
                continue
            for variant in range(2):
                seed_words = [args.seed, family_index, split_index, variant, 1927]
                rng = np.random.default_rng(np.random.SeedSequence(seed_words))
                batch = (24, 96)[variant] if split == "pool" else (48, 128)[variant]
                artifact_label = ("development", "heldout")[split_index]
                case_id = f"{family.lower()}_{artifact_label}_{variant}"
                if args.fresh_heldout:
                    case_id += f"_seed{args.seed}"
                data, reference, audit = make_case(phonon, base, rng, batch, bool(variant), bool(variant))
                input_path = pool / "inputs" / f"{case_id}.npz"
                input_path.parent.mkdir(parents=True, exist_ok=True)
                reference_path = REFERENCE / "outputs" / output_group / f"{case_id}.npz"
                reference_path.parent.mkdir(parents=True, exist_ok=True)
                baseline_path = REFERENCE / "baseline" / output_group / f"{case_id}.npz"
                strong_path = POLAR / "private/reference/author_measurements" / output_group / "strong" / f"{case_id}.npz"
                np.savez_compressed(input_path, **data)
                np.savez_compressed(reference_path, **reference)
                case = {"id": case_id, "family": family, "split": split,
                        "input": str(input_path.relative_to(PRIVATE)), "reference": str(reference_path.relative_to(PRIVATE)),
                        "baseline": str(baseline_path.relative_to(PRIVATE)), "timeout": 180, "memory_mb": 8192,
                        "keys": list(REQUIRED), "error_floor": 1e-10, "seed": seed_words, "near_gamma": bool(variant),
                        "frame": "rotated_unimodular_oblique" if variant else "original_primitive",
                        "input_sha256": digest(input_path), "reference_sha256": digest(reference_path), **audit}
                if not args.no_measure:
                    strong_execution = execute(REFERENCE / "solve.py", input_path, strong_path)
                    weak_execution = execute(baseline, input_path, baseline_path)
                    case["reference_errors"] = errors(strong_path, reference_path, data)
                    if case["reference_errors"]["polar_derivative"] > 1e-10 or case["reference_errors"]["mode_response"] > 1e-7:
                        raise RuntimeError(f"raw oracle disagreement in {case_id}: {case['reference_errors']}")
                    if audit["rust_python_max_relative_error"] > 1e-10:
                        raise RuntimeError(f"upstream backend disagreement in {case_id}")
                    strong_score = score_details(strong_path, reference_path, baseline_path, case, data)
                    weak_score = score_details(baseline_path, reference_path, baseline_path, case, data)
                    reports.append({"id": case_id, "family": family, "split": split, "strong": strong_score,
                                    "baseline": weak_score, "strong_execution": strong_execution, "baseline_execution": weak_execution})
                    if strong_score["score"] <= 0.90:
                        raise RuntimeError(f"strong reference failed {case_id}: {strong_score}")
                manifest.append(case)
                print(json.dumps({"case": case_id, "audit": audit, "measured": not args.no_measure}), flush=True)
        if family_index == 0 and not args.fresh_heldout:
            smoke, _, _ = make_case(phonon, base, np.random.default_rng(8841), 3, False, False)
            smoke_path = POLAR / "participant/input/smoke.npz"
            smoke_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(smoke_path, **smoke)
    write_json(pool / "manifest.json", manifest)
    provenance = {
        "seed": args.seed, "fresh_heldout": args.fresh_heldout,
        "upstream_repository": "https://github.com/phonopy/phonopy", "oracle_tag": "v4.1.0",
        "oracle_tag_commit": git("rev-parse", "v4.1.0").decode().strip(),
        "python_derivative_commit": "e0e7cff353bccfed8bce258ea84502347205689a",
        "rust_dispatch_commit": "01ee047591d3dd13437b123cf053bb7ae039de40",
        "group_velocity_default_commit": "94a79bd0d420bb93bf9547c53c6a76dd2284cf1e",
        "runtime": str(RUNTIME), "python": sys.version, "fixture_sha256": fixture_hashes,
        "dependencies": sorted(f"{entry.metadata['Name']}=={entry.version}" for entry in importlib.metadata.distributions(path=[str(RUNTIME)])),
        "baseline_sha256": digest(baseline), "strong_solver_sha256": digest(REFERENCE / "solve.py"),
        "export_policy": "Pinned real FC fixtures; rigid rotations and unimodular basis changes only.",
        "oracle_policy": "Rust derivative at every query, Python parity at three per case; response spectra and branch vectors use upstream GroupVelocity._perturb_D.",
        "gamma_guard": "Pinned derivative has Q_DIRECTION_TOLERANCE=1e-5; queries remain at least 2e-5 from reciprocal singularities.",
        "split_policy": "Independent SeedSequence streams keyed by material, split and variant. New heldout uses a new seed and output directory.",
        "determinism": "Input/reference arrays rebuild deterministically under recorded runtime. Timings and RSS are measured, not deterministic.",
    }
    write_json(REFERENCE / f"provenance_{output_group}.json", provenance)
    if reports:
        summary = {"strong_score": float(np.mean([record["strong"]["score"] for record in reports])),
                   "baseline_score": float(np.mean([record["baseline"]["score"] for record in reports])),
                   "cases": reports, "measurement_policy": "Trusted local calibration; per-branch RSS diagnostics are cumulative process peaks, not isolated allocations."}
        write_json(POLAR / "private/reference/author_measurements" / output_group / "calibration.json", summary)
        print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()

"""Deterministically build private cases from the official displacement-force data."""

import argparse
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import resource
import runpy
import subprocess
import sys
import time

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

PILOT = Path(__file__).resolve().parents[2]
TARGET = Path(__file__).resolve().parents[4]
RUNTIME = TARGET / "author/runtime"
SOURCES = TARGET / "author/source"
sys.path.insert(0, str(RUNTIME))

import numpy as np
import phono3py
from scipy.spatial import cKDTree
import spglib
from symfc import Symfc
from symfc.utils.utils import SymfcAtoms

from physics import fold_harmonic, harmonic_forces, invariant_errors, validate_output


CASES = [
    {"id": "initial_nacl_64_512", "family": "rocksalt_ionic", "split": "initial", "source": "phono3py/example/NaCl-rd/phono3py_params_NaCl.yaml.xz", "mode": 1, "cutoff": 4.5, "train3": 80, "test3": 20, "train2": 1},
    {"id": "initial_si_8", "family": "diamond_covalent", "split": "initial", "source": "phono3py/test/phono3py_params-Si111-rd.yaml.xz", "mode": 0, "cutoff": 4.0, "train3": 96, "test3": 32},
    {"id": "initial_gan_32", "family": "wurtzite_polar", "split": "initial", "source": "symfc/tests/dfset_GaN_222_rd.xz", "fixture": "ph_gan_222", "mode": 0, "cutoff": 4.0, "train3": 32, "test3": 8},
    {"id": "heldout_mgo_64_512", "family": "rocksalt_ionic", "split": "heldout", "source": "phono3py/test/phono3py_params_MgO-222rd-444rd.yaml.xz", "mode": 1, "cutoff": 4.0, "train3": 80, "test3": 20, "train2": 3},
    {"id": "heldout_sno2_72", "family": "rutile_oxide", "split": "heldout", "source": "symfc/tests/dfset_SnO2_223_rd.xz", "fixture": "ph_sno2_223", "mode": 0, "cutoff": 4.0, "train3": 32, "test3": 8},
    {"id": "heldout_gan_128", "family": "wurtzite_polar", "split": "heldout", "source": "symfc/tests/dfset_GaN_442_rd.xz", "fixture": "ph_gan_442", "mode": 0, "cutoff": 4.0, "train3": 32, "test3": 8},
]


def dump_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, sort_keys=True, allow_nan=False) + "\n")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atom_object(atoms):
    return SymfcAtoms(cell=atoms.cell, scaled_positions=atoms.scaled_positions, numbers=atoms.numbers)


def load_source(configuration):
    if "fixture" in configuration:
        fixtures = runpy.run_path(str(SOURCES / "symfc/tests/conftest.py"))
        atoms, displacements, forces = fixtures[configuration["fixture"]].__wrapped__()
        atoms = atom_object(atoms)
        return atoms, atoms, np.empty((0, len(atoms), 3)), np.empty((0, len(atoms), 3)), displacements, forces
    model = phono3py.load(str(SOURCES / configuration["source"]), produce_fc=False, is_nac=False)
    atoms3 = atom_object(model.supercell)
    atoms2 = atom_object(model.phonon_supercell)
    if configuration["mode"] == 1:
        displacements2 = np.asarray(model.phonon_dataset["displacements"], dtype=np.float64)
        forces2 = np.asarray(model.phonon_dataset["forces"], dtype=np.float64)
    else:
        displacements2 = np.empty((0, len(atoms2), 3))
        forces2 = np.empty_like(displacements2)
    return atoms2, atoms3, displacements2, forces2, model.displacements, model.forces


def match_atoms(transformed, positions, numbers, target_numbers=None):
    transformed = np.mod(transformed, 1.0)
    positions = np.mod(positions, 1.0)
    if target_numbers is None:
        target_numbers = numbers
    result = np.empty(len(transformed), dtype=np.int64)
    for atomic_number in np.unique(numbers):
        selected = np.flatnonzero(numbers == atomic_number)
        targets = np.flatnonzero(target_numbers == atomic_number)
        tree = cKDTree(positions[targets], boxsize=1.0)
        distances, matches = tree.query(transformed[selected])
        if np.max(distances) > 3e-6:
            raise ValueError(f"geometric atom match failed: {np.max(distances)}")
        result[selected] = targets[matches]
    return result


def geometry(atoms, suffix):
    cell = np.asarray(atoms.cell, dtype=np.float64)
    positions = np.mod(np.asarray(atoms.scaled_positions, dtype=np.float64), 1.0)
    numbers = np.asarray(atoms.numbers, dtype=np.int64)
    operations = spglib.get_symmetry((cell, positions, numbers), symprec=1e-5)
    rotations = operations["rotations"]
    translations = operations["translations"]
    identity = np.all(rotations == np.eye(3, dtype=int), axis=(1, 2))
    translation_permutations = np.asarray([match_atoms(positions + translation, positions, numbers) for translation in translations[identity]])
    representatives = []
    row_map = np.full(len(atoms), -1, dtype=np.int64)
    compact_map = np.empty((len(atoms), len(atoms)), dtype=np.int64)
    for atom in range(len(atoms)):
        if row_map[atom] >= 0:
            continue
        representative = len(representatives)
        representatives.append(atom)
        orbit = np.unique(translation_permutations[:, atom])
        row_map[orbit] = representative
        for permutation in translation_permutations:
            compact_map[permutation[atom]] = np.argsort(permutation)
    representatives = np.asarray(representatives, dtype=np.int64)
    if not np.array_equal(row_map[representatives], np.arange(len(representatives))):
        raise ValueError("invalid representative map")
    for atom in range(len(atoms)):
        if compact_map[atom, atom] != representatives[row_map[atom]]:
            raise ValueError("invalid translation-to-representative map")
    _, distinct = np.unique(rotations.reshape(-1, 9), axis=0, return_index=True)
    distinct = np.sort(distinct)
    fractional_rotations = rotations[distinct].astype(np.int64)
    fractional_translations = translations[distinct].astype(np.float64)
    permutations = np.asarray([match_atoms(positions @ rotation.T + translation, positions, numbers) for rotation, translation in zip(fractional_rotations, fractional_translations)], dtype=np.int64)
    cart_rotations = np.asarray([cell.T @ rotation @ np.linalg.inv(cell.T) for rotation in fractional_rotations])
    output = {
        "cell": cell, "positions": positions, "numbers": numbers,
        "p2s": representatives, "s2p": row_map, "compact_map": compact_map,
        "rotations": fractional_rotations, "translations": fractional_translations,
        "permutations": permutations, "cart_rotations": cart_rotations,
    }
    return {key + suffix: value for key, value in output.items()}


def support_mask(atoms, representatives, cutoff):
    positions = np.asarray(atoms.scaled_positions)
    difference = positions[:, None] - positions[None, :]
    difference -= np.rint(difference)
    distance2 = np.full(difference.shape[:2], np.inf)
    for translation in itertools.product((-1, 0, 1), repeat=3):
        cartesian = (difference + translation) @ atoms.cell
        distance2 = np.minimum(distance2, np.sum(cartesian**2, axis=2))
    close = distance2 <= (cutoff + 1e-8) ** 2
    return close[representatives, :, None] & close[representatives, None, :] & close[None, :, :]


def folding_map(input_data):
    cartesian2 = input_data["positions2"] @ input_data["cell2"]
    cartesian3 = input_data["positions3"] @ input_data["cell3"]
    result = []
    if len(input_data["p2s2"]) != len(input_data["p2s3"]):
        raise ValueError("different primitive atom counts")
    for atom2, atom3 in zip(input_data["p2s2"], input_data["p2s3"]):
        if input_data["numbers2"][atom2] != input_data["numbers3"][atom3]:
            raise ValueError("representative species/order mismatch")
        shifted = cartesian2 + cartesian3[atom3] - cartesian2[atom2]
        result.append(match_atoms(shifted @ np.linalg.inv(input_data["cell3"]), input_data["positions3"], input_data["numbers2"], input_data["numbers3"]))
    return np.asarray(result, dtype=np.int64)


def estimate(atoms, displacements, forces, orders, cutoff, expected_representatives):
    solver = Symfc(atoms, displacements=np.ascontiguousarray(displacements), forces=np.ascontiguousarray(forces), cutoff={3: cutoff}, log_level=0)
    solver.run(orders=orders, is_compact_fc=True)
    if not np.array_equal(solver.p2s_map, expected_representatives):
        raise ValueError(f"oracle representative mismatch: {solver.p2s_map} != {expected_representatives}")
    basis_sizes = {str(order): int(solver.basis_set[order].basis_set.shape[1]) for order in orders}
    return {f"fc{order}": np.asarray(solver.force_constants[order], dtype=np.float64) for order in orders}, basis_sizes


def build_case(configuration, initial_seed, heldout_seed):
    start = time.perf_counter()
    case_index = next(index for index, item in enumerate(CASES) if item["id"] == configuration["id"])
    seed = initial_seed if configuration["split"] == "initial" else heldout_seed
    generator = np.random.default_rng(np.random.SeedSequence([seed, case_index, 173]))
    atoms2, atoms3, displacements2, forces2, displacements3, forces3 = load_source(configuration)
    indices3 = generator.permutation(len(displacements3))[: configuration["train3"] + configuration["test3"]]
    train3 = indices3[: configuration["train3"]]
    test3 = indices3[configuration["train3"] :]
    indices2 = generator.permutation(len(displacements2))
    train2 = indices2[: configuration.get("train2", 0)]
    test2 = indices2[configuration.get("train2", 0) :]
    input_data = {
        "schema_version": np.asarray(1, dtype=np.int64),
        "fit_mode": np.asarray(configuration["mode"], dtype=np.int64),
        "u2": np.asarray(displacements2[train2], dtype=np.float64),
        "f2": np.asarray(forces2[train2], dtype=np.float64),
        "u3": np.asarray(displacements3[train3], dtype=np.float64),
        "f3": np.asarray(forces3[train3], dtype=np.float64),
        "cutoff3": np.asarray(configuration["cutoff"], dtype=np.float64),
    }
    input_data.update(geometry(atoms2, "2"))
    input_data.update(geometry(atoms3, "3"))
    input_data["fold2to3"] = folding_map(input_data)
    input_data["triplet_mask3"] = support_mask(atoms3, input_data["p2s3"], configuration["cutoff"])
    if configuration["mode"] == 0:
        result, basis_sizes = estimate(atoms3, input_data["u3"], input_data["f3"], [2, 3], configuration["cutoff"], input_data["p2s3"])
    else:
        result, basis_sizes = estimate(atoms2, input_data["u2"], input_data["f2"], [2], configuration["cutoff"], input_data["p2s2"])
        harmonic = fold_harmonic(result["fc2"], input_data)
        residual = input_data["f3"] - harmonic_forces(harmonic, input_data["u3"], input_data["s2p3"], input_data["compact_map3"])
        cubic, cubic_sizes = estimate(atoms3, input_data["u3"], residual, [3], configuration["cutoff"], input_data["p2s3"])
        result.update(cubic)
        basis_sizes.update(cubic_sizes)
    validate_output(result, input_data)
    errors = invariant_errors(result, input_data)
    if max(errors.values()) > 1e-6:
        raise ValueError(f"reference invariance validation failed: {errors}")
    result.update({
        "heldout_u2": np.asarray(displacements2[test2], dtype=np.float64),
        "heldout_f2": np.asarray(forces2[test2], dtype=np.float64),
        "heldout_u3": np.asarray(displacements3[test3], dtype=np.float64),
        "heldout_f3": np.asarray(forces3[test3], dtype=np.float64),
    })
    private = PILOT / "private"
    folder = private / "challenge_pool" / configuration["id"]
    folder.mkdir(parents=True, exist_ok=True)
    input_path = folder / "input.npz"
    reference_path = private / "reference" / (configuration["id"] + ".npz")
    np.savez_compressed(input_path, **input_data)
    np.savez_compressed(reference_path, **result)
    source_files = [configuration["source"]]
    if "fixture" in configuration:
        source_files.append("symfc/tests/conftest.py")
    metadata = {
        "id": configuration["id"], "family": configuration["family"], "split": "pool" if configuration["split"] == "initial" else "heldout",
        "input": str(input_path.relative_to(private)), "reference": str(reference_path.relative_to(private)),
        "baseline": "reference/" + configuration["id"] + ".baseline.npz",
        "timeout": 180, "memory_mb": 8192, "keys": ["fc2", "fc3"], "core": True,
        "files": {"input": str(input_path.relative_to(private)), "reference": str(reference_path.relative_to(private)), "baseline": "reference/" + configuration["id"] + ".baseline.npz"},
        "fit_mode": configuration["mode"], "n2": len(atoms2), "n3": len(atoms3), "primitive_atoms": len(input_data["p2s2"]),
        "train2_count": len(train2), "test2_count": len(test2), "train3_count": len(train3), "test3_count": len(test3),
        "basis_dimensions_private": basis_sizes, "cutoff3_angstrom": configuration["cutoff"],
        "seed": seed, "train2_indices": train2.tolist(), "test2_indices": test2.tolist(),
        "train3_indices": train3.tolist(), "test3_indices": test3.tolist(),
        "sources": [{"path": relative, "sha256": sha256(SOURCES / relative), "url": "https://github.com/" + {"symfc": "symfc/symfc", "phonopy": "phonopy/phonopy", "phono3py": "phonopy/phono3py"}[relative.split("/")[0]] + "/blob/" + subprocess.check_output(["git", "-C", str(SOURCES / relative.split("/")[0]), "rev-parse", "HEAD"], text=True).strip() + "/" + relative.split("/", 1)[1]} for relative in source_files],
        "input_sha256": sha256(input_path), "reference_sha256": sha256(reference_path),
    }
    dump_json(folder / "metadata.json", metadata)
    dump_json(private / "reference" / (configuration["id"] + ".build.json"), {
        "id": configuration["id"], "seconds": time.perf_counter() - start,
        "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "invariant_errors": errors, "reference_validated": True,
    })
    print(json.dumps({"id": configuration["id"], "n2": len(atoms2), "n3": len(atoms3), "basis": basis_sizes, "seconds": time.perf_counter() - start, "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


def write_smoke():
    path = PILOT / "private/challenge_pool/initial_si_8/input.npz"
    if not path.exists():
        return
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    data["u3"] = data["u3"][:6]
    data["f3"] = data["f3"][:6]
    folder = PILOT / "participant/input"
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / "smoke.npz", **data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-seed", type=int, default=230105784)
    parser.add_argument("--heldout-seed", type=int, default=870341)
    parser.add_argument("--case", action="append", choices=[item["id"] for item in CASES])
    parser.add_argument("--worker", choices=[item["id"] for item in CASES])
    args = parser.parse_args()
    expected = {"phonopy": "2.43.4", "phono3py": "3.19.2", "symfc": "1.5.4", "spglib": "2.5.0"}
    versions = {name: importlib.metadata.version(name) for name in expected}
    if versions != expected:
        raise RuntimeError(f"oracle runtime mismatch: {versions} != {expected}")
    if args.worker:
        configuration = next(item for item in CASES if item["id"] == args.worker)
        build_case(configuration, args.initial_seed, args.heldout_seed)
        return
    selected = [item for item in CASES if not args.case or item["id"] in args.case]
    for configuration in selected:
        subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", configuration["id"], "--initial-seed", str(args.initial_seed), "--heldout-seed", str(args.heldout_seed)], check=True, cwd=PILOT)
    manifest = []
    for configuration in CASES:
        metadata_path = PILOT / "private/challenge_pool" / configuration["id"] / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            if metadata["split"] == "initial":
                metadata["split"] = "pool"
                dump_json(metadata_path, metadata)
            manifest.append(metadata)
    dump_json(PILOT / "private/challenge_pool/manifest.json", manifest)
    dump_json(PILOT / "private/reference/provenance.json", {
        "runtime_versions": versions,
        "additional_versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pytest")},
        "runtime": "author/runtime", "source_root": "author/source",
        "source_commits": {name: subprocess.check_output(["git", "-C", str(SOURCES / name), "rev-parse", "HEAD"], text=True).strip() for name in ("symfc", "phonopy", "phono3py")},
        "oracle_tag": "https://github.com/symfc/symfc/tree/v1.5.4",
        "oracle_tag_commit": "7b774611f10a5930c9e760a759e304020217c087",
        "initial_seed": args.initial_seed, "heldout_seed": args.heldout_seed,
        "snapshots": "Unmodified official stored displacement/force observations; only deterministic snapshot selection is applied.",
        "geometry": "Geometry comes from the dataset or its official fixture. Public operations and compact/folding maps are geometry-only.",
        "cutoff": "Public finite-range restriction applies to fc3 only; harmonic 512-atom supercells are retained.",
        "threads": {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    })
    write_smoke()


if __name__ == "__main__":
    main()

"""Freeze source-grounded cases, weak calibration, and strong labels before scoring."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import scipy.linalg as la

from reference_engine import PILOT, ROOT, imported_model, sample, solve, tbmodels
from invariants import check
from metrics import score, track_metrics

sys.path.insert(0, str(PILOT / "participant/workspace"))

import pipeline
from historical_model import Model as HistoricalModel


SOURCE = ROOT / "authoring/sources/TBmodels"
REFERENCE_PIN = "39d7eb096d809137373774ef6ba337fdf36349bc"
PATTERNS = (("silicon", "wannier"), ("bi", "wannier"), ("silicon", "nearest_atom"),
            ("bi", "nearest_atom"), ("inas", "wannier"), ("inas", "nearest_atom"))
SEEDS = {"test": tuple(range(120031, 120037)), "challenge": tuple(range(470041, 470047)),
         "confirmation": tuple(range(930071, 930077))}
HDF5 = {"silicon": "examples/symmetrization/nonsymmorphic_Si/data/model_nosym.hdf5",
        "inas": "tests/samples/InAs_nosym.hdf5"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def save_model(path, model):
    vectors = sorted(model.hop)
    np.savez_compressed(path, uc=model.uc, pos=model.pos, R=np.array(vectors, dtype=int),
                        hop=np.array([model.hop[vector] for vector in vectors]))


def frame_transform(rng, confirmation=False):
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    stretch = np.diag([1.37, 0.74, 1.11] if not confirmation else [0.68, 1.46, 1.23])
    stretch[0, 1] = rng.uniform(-0.3, 0.3)
    stretch[2, 0] = rng.uniform(-0.3, 0.3)
    return stretch @ rotation


def import_files(case, material, kind, rng, confirmation):
    sources = []
    if material == "inas":
        source = SOURCE / HDF5["inas"]
        sources.append(source)
        model = tbmodels.Model.from_hdf5_file(source)
        model.to_hr_file(case / "import_hr.dat")
        cell = model.uc
        centres = np.asarray(model.pos) @ cell
        atom_positions = np.unique(np.asarray(model.pos), axis=0) @ cell
        atom_kinds = ["In", "As"]
        size = int(model.size)
        wsvec = None
    else:
        files = {key: SOURCE / "tests/samples" / filename for key, filename in
                 {"hr": f"{material}_hr.dat", "wsvec": f"{material}_wsvec.dat",
                  "xyz": f"{material}_centres.xyz", "win": f"{material}.win"}.items()}
        sources.extend(files.values())
        shutil.copyfile(files["hr"], case / "import_hr.dat")
        shutil.copyfile(files["wsvec"], case / "import_wsvec.dat")
        with files["win"].open() as handle:
            cell = tbmodels.Model._read_win(handle)["unit_cell_cart"]
        with files["xyz"].open() as handle:
            centres, atoms = tbmodels.Model._read_xyz(handle)
        centres = np.asarray(centres)
        atom_positions = np.array([atom.pos for atom in atoms])
        atom_kinds = [atom.kind for atom in atoms]
        size = len(centres)
        wsvec = "import_wsvec.dat"
    frame = frame_transform(rng, confirmation)
    metric_trials = 0
    if material == "silicon" and kind == "nearest_atom" and not confirmation:
        differences = centres[:, None] - atom_positions[None, :]
        fractional_choice = np.argmin(np.linalg.norm(differences @ np.linalg.inv(cell), axis=2), axis=1)
        for metric_trials in range(1, 1001):
            stretch = np.diag(np.exp(rng.uniform(-1.8, 1.8, size=3)))
            stretch[0, 1] = rng.uniform(-0.8, 0.8)
            stretch[2, 0] = rng.uniform(-0.8, 0.8)
            rotation, _ = np.linalg.qr(frame)
            candidate_frame = stretch @ rotation
            cartesian_choice = np.argmin(np.linalg.norm(differences @ candidate_frame, axis=2), axis=1)
            if np.any(cartesian_choice != fractional_choice) and len(np.unique(cartesian_choice)) > 1:
                frame = candidate_frame
                break
        else:
            raise RuntimeError("No source-grounded Cartesian-metric separator found")
    origin = rng.uniform(-0.65, 0.65, size=3)
    transformed_cell = cell @ frame
    transformed_centres = (centres + origin @ cell) @ frame
    transformed_atoms = (atom_positions + origin @ cell) @ frame
    atom_order = rng.permutation(len(atom_positions))
    atom_rows = [f"{atom_kinds[index]} " + " ".join(f"{value:.17g}" for value in transformed_atoms[index]) for index in atom_order]
    xyz = [str(size + len(atom_positions)), "Source-derived Cartesian centres and explicit atoms"]
    xyz += ["X " + " ".join(f"{value:.17g}" for value in row) for row in transformed_centres]
    xyz += atom_rows
    (case / "import_centres.xyz").write_text("\n".join(xyz) + "\n")
    win = ["begin unit_cell_cart", "ang"]
    win += [" ".join(f"{value:.17g}" for value in row) for row in transformed_cell]
    win += ["end unit_cell_cart"]
    (case / "import.win").write_text("\n".join(win) + "\n")
    phases = rng.uniform(-np.pi, np.pi, size=size)
    energy_scale = rng.uniform(0.75, 1.25)
    lines = (case / "import_hr.dat").read_text().splitlines()
    block_count = int(lines[2])
    header_size = 3 + (block_count + 14) // 15
    output = lines[:header_size]
    for line in lines[header_size:]:
        if not line.strip():
            continue
        fields = line.split()
        orbital_one, orbital_two = int(fields[3]) - 1, int(fields[4]) - 1
        value = complex(float(fields[5]), float(fields[6])) * energy_scale * np.exp(1j * (phases[orbital_two] - phases[orbital_one]))
        output.append(" ".join(fields[:5]) + f" {value.real:.17g} {value.imag:.17g}")
    (case / "import_hr.dat").write_text("\n".join(output) + "\n")
    replication = [2, 1, 1] if not confirmation else [1, 2, 1]
    count = size * 2
    spec = {"hr": "import_hr.dat", "wsvec": wsvec, "xyz": "import_centres.xyz", "win": "import.win",
            "pos_kind": kind, "supercell": replication, "permutation": rng.permutation(count).tolist(),
            "kpoints": rng.uniform(-0.7, 0.7, size=(11, 3)).tolist()}
    metadata = {"material": material, "primitive_orbitals": size, "output_orbitals": count,
                "frame": frame.tolist(), "origin_old_reduced": origin.tolist(), "atom_order": atom_order.tolist(),
                "orbital_phases": phases.tolist(), "energy_scale": energy_scale, "metric_selection_trials": metric_trials,
                "source_files": [{"path": str(path.relative_to(SOURCE)), "sha256": digest(path)} for path in sources]}
    return spec, metadata


def mapping_files(case, material, rng, confirmation, smoke=False):
    source = SOURCE / HDF5[material]
    original = tbmodels.Model.from_hdf5_file(source)
    replication = [1, 1, 1] if material == "silicon" else ([2, 1, 1] if not confirmation else [1, 1, 2])
    original = original.supercell(replication)
    source_order = rng.permutation(original.size)
    original = original.slice_orbitals(source_order)
    frame = frame_transform(rng, confirmation)
    phases = np.exp(1j * rng.uniform(-np.pi, np.pi, size=original.size))
    original = tbmodels.Model(uc=original.uc @ frame, pos=original.pos,
                              hop={vector: phases.conj()[:, None] * matrix * phases[None, :]
                                   for vector, matrix in original.hop.items()}, contains_cc=False)
    save_model(case / "mapping_model.npz", original)
    historical = HistoricalModel(uc=original.uc, pos=original.pos, hop=original.hop, contains_cc=False)
    permutation = rng.permutation(original.size).tolist()
    kpoints = rng.uniform(-0.8, 0.8, size=(13, 3))
    candidates = [np.array([[3, 2, 0], [1, 1, 0], [0, 0, 1]]),
                  np.array([[2, 3, 0], [1, 2, 0], [0, 0, 1]])]
    for trial in range(300):
        transform = candidates[trial % len(candidates)].copy()
        axes = rng.permutation(3)
        transform = transform[axes][:, axes]
        if confirmation:
            transform = np.rint(np.linalg.inv(transform)).astype(int)
        offset = rng.uniform(-0.6, 0.6, size=3)
        if trial % 3 == 0:
            offset[trial % 3] = np.asarray(original.pos)[0, trial % 3] + rng.choice([-1, 1]) * 2e-10
        cartesian = bool(rng.integers(2))
        if smoke:
            transform = np.eye(3, dtype=int)
        target_cell = np.asarray(transform @ original.uc if cartesian else transform).tolist()
        target_offset = np.asarray(offset @ original.uc if cartesian else offset).tolist()
        try:
            reference = original.change_unit_cell(uc=target_cell, offset=target_offset, cartesian=cartesian)
            weak = historical.change_unit_cell(uc=target_cell, offset=target_offset, cartesian=cartesian)
        except (ValueError, AssertionError):
            continue
        difference = np.linalg.norm(reference.hamilton(kpoints) - weak.hamilton(kpoints))
        if smoke or difference > 1e-3:
            break
    else:
        raise RuntimeError("No genuine historical rounding failure found")
    spec = {"model": "mapping_model.npz", "uc": np.asarray(target_cell).tolist(),
            "offset": np.asarray(target_offset).tolist(), "cartesian": cartesian,
            "permutation": permutation, "kpoints": kpoints.tolist()}
    metadata = {"material": material, "source_file": str(source.relative_to(SOURCE)), "sha256": digest(source),
                "supercell": replication, "output_orbitals": int(original.size), "source_order": source_order.tolist(),
                "frame": frame.tolist(), "orbital_phases": np.angle(phases).tolist(),
                "integer_transform": transform.tolist(), "origin_old_reduced": offset.tolist(),
                "historical_matrix_difference": float(difference), "selection_trials": trial + 1}
    return spec, metadata


def ablations(case, spec, reference, weak, weak_errors):
    variants = {}
    for name, prefix in (("import_repaired_only", "import"), ("mapping_repaired_only", "map"), ("bands_only", None)):
        candidate = dict(weak)
        for key, value in reference.items():
            if (prefix and key.startswith(prefix + "_")) or (prefix is None and key.endswith("_bands")):
                candidate[key] = value
        variants[name] = {track: score(track_metrics(candidate, reference, track)[0], weak_errors[track]) for track in ("import", "map")}
    if spec["import"].get("wsvec"):
        _, model = imported_model(case, spec["import"], ignore_wsvec=True)
        candidate = dict(reference)
        candidate.update(sample(model, spec["import"]["kpoints"], spec["import"]["permutation"], "import"))
        error = track_metrics(candidate, reference, "import")[0]
        variants["ignore_wsvec"] = {"error": error, "score": score(error, weak_errors["import"])}
    if spec["import"]["pos_kind"] == "nearest_atom":
        with (case / spec["import"]["xyz"]).open() as handle:
            centres, atoms = tbmodels.Model._read_xyz(handle)
        with (case / spec["import"]["win"]).open() as handle:
            cell = tbmodels.Model._read_win(handle)["unit_cell_cart"]
        reduced_centres = np.asarray(centres) @ np.linalg.inv(cell)
        reduced_atoms = np.asarray([atom.pos for atom in atoms]) @ np.linalg.inv(cell)
        fractional_choice = np.argmin(np.linalg.norm(reduced_centres[:, None] - reduced_atoms[None, :], axis=2), axis=1)
        cartesian_choice = np.argmin(np.linalg.norm(np.asarray(centres)[:, None] - np.asarray([atom.pos for atom in atoms])[None, :], axis=2), axis=1)
        variants["fractional_metric"] = {"wrong_assignments": int(np.sum(fractional_choice != cartesian_choice)), "orbitals": len(centres)}
    return variants


def make_case(case, seed, pattern_index, confirmation=False, smoke=False):
    case.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    material, kind = PATTERNS[pattern_index]
    import_spec, import_meta = import_files(case, material, kind, rng, confirmation)
    mapping_material = "silicon" if pattern_index % 2 == 0 else "inas"
    mapping_spec, mapping_meta = mapping_files(case, mapping_material, rng, confirmation, smoke)
    if smoke:
        import_spec["kpoints"] = import_spec["kpoints"][:3]
        mapping_spec["kpoints"] = mapping_spec["kpoints"][:3]
    spec = {"format_version": 1, "import": import_spec, "mapping": mapping_spec}
    dump_json(case / "case.json", spec)
    return spec, {"seed": seed, "import": import_meta, "mapping": mapping_meta}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("test", "challenge", "confirmation", "all"), default="all")
    parser.add_argument("--case-index", type=int, choices=range(len(PATTERNS)))
    arguments = parser.parse_args()
    actual_pin = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    if actual_pin != REFERENCE_PIN:
        raise RuntimeError(f"Reference source changed: {actual_pin}")
    smoke = PILOT / "participant/input/smoke"
    if not (smoke / "case.json").exists():
        make_case(smoke, 5019, 0, smoke=True)
    splits = list(SEEDS) if arguments.split == "all" else [arguments.split]
    for split in splits:
        manifest = {"version": 1, "split": split, "reference_pin": REFERENCE_PIN,
                    "nearest_atom_reference_pin": "84cdd38d47243208b49c88e8e41c449201530df7", "cases": []}
        if arguments.case_index is not None:
            manifest = json.loads((PILOT / "private/reference" / f"manifest_{split}.json").read_text())
        for pattern_index, seed in enumerate(SEEDS[split]):
            if arguments.case_index is not None and pattern_index != arguments.case_index:
                continue
            started = time.monotonic()
            identifier = f"{split}_{pattern_index + 1:02d}"
            case = PILOT / "private/challenge_pool" / split / identifier
            spec, metadata = make_case(case, seed, pattern_index, confirmation=split == "confirmation")
            reference = solve(case)
            weak = pipeline.solve(case)
            weak_errors = {prefix: track_metrics(weak, reference, prefix)[0] for prefix in ("import", "map")}
            if not all(value > 1e-7 for value in weak_errors.values()):
                raise AssertionError((identifier, weak_errors))
            invariants = check(case, reference)
            label = PILOT / "private/reference" / split / f"{identifier}.npz"
            label.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(label, **reference)
            weak_path = label.with_name(identifier + "_weak.npz")
            np.savez_compressed(weak_path, **weak)
            record = {"id": identifier, "case": str(case.relative_to(PILOT / "private")),
                      "reference": str(label.relative_to(PILOT / "private")), "reference_sha256": digest(label),
                      "input_sha256": {path.name: digest(path) for path in sorted(case.iterdir()) if path.is_file()},
                      "import_family": "cartesian_wsvec" if spec["import"]["pos_kind"] == "wannier" else "nearest_atom",
                      "weak_errors": weak_errors, "provenance": metadata,
                      "invariants": invariants, "ablations": ablations(case, spec, reference, weak, weak_errors),
                      "build_runtime_seconds": time.monotonic() - started}
            manifest["cases"] = sorted([item for item in manifest["cases"] if item["id"] != identifier] + [record], key=lambda item: item["id"])
            print(identifier, "weak_errors", weak_errors, "max_invariant", max(invariants.values()), flush=True)
        dump_json(PILOT / "private/reference" / f"manifest_{split}.json", manifest)
    dump_json(PILOT / "private/reference/build_metadata.json", {"reference_pin": actual_pin,
              "tbmodels_version": tbmodels.__version__, "source_module": str(Path(tbmodels.__file__).resolve()),
              "seeds": SEEDS, "confirmation_reservation": "Disjoint seeds, inverse shears, new embedding stretches, and new physical-supercell axes; never copied from the test/challenge pool."})


if __name__ == "__main__":
    main()

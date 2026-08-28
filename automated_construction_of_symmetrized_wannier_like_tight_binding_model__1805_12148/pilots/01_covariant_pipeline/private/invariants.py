"""Independent algebraic checks, including a direct Wannier text calculation."""

import itertools
import json
from pathlib import Path

import numpy as np


def direct_import(case, spec):
    xyz_lines = (case / spec["xyz"]).read_text().splitlines()[2:]
    centres = np.array([[float(value) for value in row.split()[1:]] for row in xyz_lines if row.split()[0] == "X"])
    atoms = np.array([[float(value) for value in row.split()[1:]] for row in xyz_lines if row.split()[0] != "X"])
    win_lines = (case / spec["win"]).read_text().splitlines()
    start = next(index for index, line in enumerate(win_lines) if line.lower().strip() == "begin unit_cell_cart")
    cell = np.array([[float(value) for value in line.split()] for line in win_lines[start + 2:start + 5]])
    positions = centres
    if spec["pos_kind"] == "nearest_atom":
        distances = np.sum((centres[:, None] - atoms[None, :]) ** 2, axis=2)
        positions = atoms[np.argmin(distances, axis=1)]
    positions = positions @ np.linalg.inv(cell)
    offsets = np.floor(positions).astype(int)
    canonical = positions - offsets
    translations = {}
    if spec.get("wsvec"):
        iterator = iter((case / spec["wsvec"]).read_text().splitlines()[1:])
        for line in iterator:
            values = tuple(int(value) for value in line.split())
            count = int(next(iterator))
            translations[values] = [np.fromstring(next(iterator), sep=" ", dtype=int) for _ in range(count)]
    iterator = iter((case / spec["hr"]).read_text().splitlines())
    next(iterator)
    size = int(next(iterator))
    block_count = int(next(iterator))
    degeneracies = []
    while len(degeneracies) < block_count:
        degeneracies.extend(int(value) for value in next(iterator).split())
    replication = np.array(spec["supercell"], dtype=int)
    images = np.array(list(itertools.product(*(range(value) for value in replication))))
    dimension = size * len(images)
    kpoints = np.asarray(spec["kpoints"])
    matrices = np.zeros((len(kpoints), dimension, dimension), dtype=complex)
    lookup = {tuple(image): index for index, image in enumerate(images)}
    record_index = 0
    for line in iterator:
        if not line.strip():
            continue
        fields = line.split()
        vector = np.array([int(value) for value in fields[:3]])
        orbital_one, orbital_two = int(fields[3]) - 1, int(fields[4]) - 1
        value = complex(float(fields[5]), float(fields[6])) / degeneracies[record_index // size ** 2]
        record_index += 1
        if value == 0:
            continue
        shifts = translations.get((*vector, orbital_one + 1, orbital_two + 1), [np.zeros(3, dtype=int)])
        for shift in shifts:
            corrected = vector + shift + offsets[orbital_two] - offsets[orbital_one]
            for image_index, image in enumerate(images):
                target = image + corrected
                destination = lookup[tuple(target % replication)]
                lattice_vector = target // replication
                matrices[:, image_index * size + orbital_one, destination * size + orbital_two] += (
                    value / len(shifts) * np.exp(2j * np.pi * (kpoints @ lattice_vector))
                )
    permutation = spec["permutation"]
    positions = np.concatenate([(canonical + image) / replication for image in images])[permutation]
    matrices = matrices[:, permutation][:, :, permutation]
    phases = np.exp(2j * np.pi * kpoints @ positions.T)
    return positions, phases.conj()[:, :, None] * matrices * phases[:, None, :], matrices


def check(case, result):
    from reference_engine import imported_model, load_model

    case = Path(case)
    spec = json.loads((case / "case.json").read_text())
    residuals = {}
    for prefix, track in (("import", "import"), ("map", "mapping")):
        positions = result[f"{prefix}_pos"]
        kpoints = np.asarray(spec[track]["kpoints"])
        phases = np.exp(2j * np.pi * kpoints @ positions.T)
        matrix_one = result[f"{prefix}_h1"]
        matrix_two = result[f"{prefix}_h2"]
        residuals[f"{prefix}_hermiticity"] = float(np.max(np.abs(matrix_two - matrix_two.conj().transpose(0, 2, 1))))
        residuals[f"{prefix}_conventions"] = float(np.max(np.abs(matrix_one - phases.conj()[:, :, None] * matrix_two * phases[:, None, :])))
    direct_pos, direct_h1, direct_h2 = direct_import(case, spec["import"])
    residuals["direct_import_pos"] = float(np.max(np.abs(result["import_pos"] - direct_pos)))
    residuals["direct_import_h1"] = float(np.max(np.abs(result["import_h1"] - direct_h1)))
    residuals["direct_import_h2"] = float(np.max(np.abs(result["import_h2"] - direct_h2)))
    primitive, _ = imported_model(case, spec["import"])
    replication = np.array(spec["import"]["supercell"])
    kpoints = np.asarray(spec["import"]["kpoints"])
    folded = np.concatenate([np.linalg.eigvalsh(primitive.hamilton((kpoints + image) / replication))
                             for image in itertools.product(*(range(value) for value in replication))], axis=1)
    residuals["supercell_band_folding"] = float(np.max(np.abs(np.sort(folded, axis=1) - result["import_bands"])))
    mapping = spec["mapping"]
    original = load_model(case / mapping["model"])
    transform = np.array(mapping["uc"])
    if mapping["cartesian"]:
        transform = transform @ np.linalg.inv(original.uc)
    transform = np.rint(transform).astype(int)
    old_kpoints = np.asarray(mapping["kpoints"]) @ np.linalg.inv(transform).T
    old_h1 = original.hamilton(old_kpoints, convention=1)
    permutation = mapping["permutation"]
    old_h1 = old_h1[:, permutation][:, :, permutation]
    residuals["mapping_covariance"] = float(np.max(np.abs(result["map_h1"] - old_h1)))
    residuals["mapping_bands"] = float(np.max(np.abs(result["map_bands"] - np.linalg.eigvalsh(old_h1))))
    mapped = original.change_unit_cell(uc=mapping["uc"], offset=mapping["offset"], cartesian=mapping["cartesian"])
    offset_cartesian = np.asarray(mapping["offset"])
    if not mapping["cartesian"]:
        offset_cartesian = offset_cartesian @ original.uc
    restored = mapped.change_unit_cell(uc=original.uc, offset=-offset_cartesian, cartesian=True)
    residuals["inverse_cell_h1"] = float(np.max(np.abs(restored.hamilton(old_kpoints, convention=1) - original.hamilton(old_kpoints, convention=1))))
    if not all(np.isfinite(value) and value < 2e-7 for value in residuals.values()):
        raise AssertionError(residuals)
    return residuals

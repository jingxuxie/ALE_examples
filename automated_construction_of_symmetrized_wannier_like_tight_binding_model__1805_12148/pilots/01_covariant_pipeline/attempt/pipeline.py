"""Covariant Wannier90 import and independent unit-cell transport."""

import argparse
import json
from pathlib import Path

import numpy as np

from historical_model import Model
from import_atom import AtomLoader
from import_xyz import CartesianLoader


def sample(model, kpoints, permutation, prefix):
    positions = np.asarray(model.pos)[permutation]
    result = {f"{prefix}_pos": positions}
    matrices = np.asarray(model.hamilton(kpoints, convention=2))
    result[f"{prefix}_h2"] = matrices[:, permutation][:, :, permutation]
    phases = np.exp(2j * np.pi * np.asarray(kpoints) @ positions.T)
    result[f"{prefix}_h1"] = (
        phases.conj()[:, :, None] * result[f"{prefix}_h2"] * phases[:, None, :]
    )
    result[f"{prefix}_bands"] = np.linalg.eigvalsh(result[f"{prefix}_h2"])
    return result


def solve(case):
    case = Path(case)
    spec = json.loads((case / "case.json").read_text())
    if spec["format_version"] != 1:
        raise ValueError('Unsupported case format version.')
    imported = spec["import"]
    if imported["pos_kind"] not in ("wannier", "nearest_atom"):
        raise ValueError('Unknown centre assignment.')
    loader = CartesianLoader if imported["pos_kind"] == "wannier" else AtomLoader
    kwargs = {f"{key}_file": str(case / imported[key]) for key in ("hr", "win", "xyz", "wsvec") if imported.get(key)}
    if imported["pos_kind"] == "nearest_atom":
        kwargs["pos_kind"] = "nearest_atom"
    model = loader.from_wannier_files(
        **kwargs, ignore_orbital_order=True
    ).supercell(imported["supercell"])
    result = sample(model, imported["kpoints"], imported["permutation"], "import")
    mapping = spec["mapping"]
    with np.load(case / mapping["model"], allow_pickle=False) as data:
        model = Model(uc=data["uc"], pos=data["pos"],
                      hop={tuple(vector): matrix for vector, matrix in zip(data["R"], data["hop"])},
                      contains_cc=False)
    model = model.change_unit_cell(uc=mapping["uc"], offset=mapping["offset"], cartesian=mapping["cartesian"])
    result.update(sample(model, mapping["kpoints"], mapping["permutation"], "map"))
    result["map_uc"] = model.uc
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **solve(args.input))


if __name__ == "__main__":
    main()

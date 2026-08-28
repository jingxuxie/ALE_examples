"""Author-only executable oracle, never imported by the evaluator."""

import json
from pathlib import Path
import sys

import numpy as np


PILOT = Path(__file__).resolve().parents[1]
ROOT = PILOT.parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "authoring/sources/TBmodels/src"), str(ROOT / "authoring/vendor")]

import tbmodels

from atom_reference import PinnedAtomLoader


def load_model(filename):
    with np.load(filename, allow_pickle=False) as arrays:
        return tbmodels.Model(uc=arrays["uc"], pos=arrays["pos"],
                              hop={tuple(vector): matrix for vector, matrix in zip(arrays["R"], arrays["hop"])},
                              contains_cc=False)


def imported_model(case, spec, ignore_wsvec=False):
    kwargs = {f"{key}_file": str(case / spec[key]) for key in ("hr", "win", "xyz", "wsvec") if spec.get(key)}
    if ignore_wsvec:
        kwargs.pop("wsvec_file", None)
    loader = PinnedAtomLoader if spec["pos_kind"] == "nearest_atom" else tbmodels.Model
    model = loader.from_wannier_files(**kwargs, pos_kind=spec["pos_kind"])
    return model, model.supercell(spec["supercell"])


def sample(model, kpoints, permutation, prefix):
    result = {f"{prefix}_pos": np.asarray(model.pos)[permutation]}
    for convention in (1, 2):
        matrices = model.hamilton(kpoints, convention=convention)
        result[f"{prefix}_h{convention}"] = matrices[:, permutation][:, :, permutation]
    result[f"{prefix}_bands"] = np.linalg.eigvalsh(result[f"{prefix}_h2"])
    return result


def solve(case):
    case = Path(case)
    spec = json.loads((case / "case.json").read_text())
    imported = spec["import"]
    _, model = imported_model(case, imported)
    result = sample(model, imported["kpoints"], imported["permutation"], "import")
    mapping = spec["mapping"]
    model = load_model(case / mapping["model"])
    model = model.change_unit_cell(uc=mapping["uc"], offset=mapping["offset"], cartesian=mapping["cartesian"])
    result.update(sample(model, mapping["kpoints"], mapping["permutation"], "map"))
    result["map_uc"] = model.uc
    return result

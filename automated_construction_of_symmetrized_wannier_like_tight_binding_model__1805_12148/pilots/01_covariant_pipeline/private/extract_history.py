"""Reproduce the public extracts from immutable local Git objects."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess


PILOT = Path(__file__).resolve().parents[1]
ROOT = PILOT.parents[1]
SOURCE = ROOT / "authoring/sources/TBmodels"
PINS = {
    "core": "24c3d2b3420d7b4b34ae15c636ea2f3685fbf02d",
    "xyz": "a93b8f805b3ade4436a89dffb209ae1d2f857dbd",
    "atom": "0168836c6bb2c04ac7a9d4ac6682fca47512ea4c",
}


def install(relative, text):
    destination = PILOT / relative
    if destination.exists():
        if destination.read_text() != text:
            raise RuntimeError(f"Refusing to overwrite changed extract: {destination}")
        return
    patch = f"*** Begin Patch\n*** Add File: {destination}\n"
    patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)


def extract(pin, names):
    text = subprocess.check_output(
        ["git", "-C", str(SOURCE), "show", f"{pin}:tbmodels/_tb_model.py"],
        text=True,
    )
    model = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == "Model")
    methods = {node.name: node for node in model.body if isinstance(node, ast.FunctionDef)}
    selected = []
    provenance = []
    for name in names:
        node = methods[name]
        start = min([node.lineno] + [item.lineno for item in node.decorator_list])
        segment = "\n".join(text.splitlines()[start - 1:node.end_lineno]) + "\n"
        selected.append(segment)
        provenance.append({"commit": pin, "file": "tbmodels/_tb_model.py", "method": name,
                           "start_line": start, "end_line": node.end_lineno,
                           "sha256": hashlib.sha256(segment.encode()).hexdigest()})
    return "\n".join(selected), provenance


def main():
    methods = ["__init__", "_init_size", "_init_dim", "_init_hop_pos", "_map_to_uc",
               "_reduce_hop", "_map_hop_positive_R", "_check_size_hop", "_check_dim",
               "from_hop_list", "_read_hr", "_empty_matrix", "_input_kwargs",
               "hamilton", "slice_orbitals", "supercell", "change_unit_cell"]
    core, provenance = extract(PINS["core"], methods)
    parsers, parser_provenance = extract(PINS["atom"], ["_async_parse", "_read_wsvec", "_read_xyz", "_read_win"])
    header = '''"""Historical TBmodels dense subset; see HISTORY.md for provenance."""

from __future__ import annotations

import collections as co
import itertools
import re
import typing as ty
import warnings

import numpy as np
import scipy.linalg as la

from dense_support import sp

HoppingType = ty.Dict[ty.Tuple[int, ...], ty.Any]


class Model:
    def set_sparse(self, sparse=False):
        if sparse:
            raise ValueError("This historical extraction supports dense matrices only.")
        self._sparse = False
        self._matrix_type = np.array

    def _array_cast(self, value):
        return np.asarray(value)

'''
    install("participant/workspace/historical_model.py", header + core + "\n" + parsers)
    for key, classname in [("xyz", "CartesianLoader"), ("atom", "AtomLoader")]:
        routine, records = extract(PINS[key], ["from_wannier_files"])
        install(f"participant/workspace/import_{key}.py",
                f'"""Unrepaired historical import path ({PINS[key]})."""\n\n'
                "import numpy as np\nimport scipy.linalg as la\nfrom historical_model import Model\n\n\n"
                f"class {classname}(Model):\n" + routine)
        provenance.extend(records)
    provenance.extend(parser_provenance)
    fixed_pin = "84cdd38d47243208b49c88e8e41c449201530df7"
    fixed, fixed_records = extract(fixed_pin, ["from_wannier_files"])
    install("private/atom_reference.py",
            '"""Official fixed explicit-atom semantics, author-only."""\n\n'
            "import numpy as np\nimport scipy.linalg as la\nfrom tbmodels import Model\n\n\n"
            "class PinnedAtomLoader(Model):\n" + fixed)
    provenance.extend(fixed_records)
    (PILOT / "private/reference").mkdir(parents=True, exist_ok=True)
    (PILOT / "private/reference/extraction.json").write_text(json.dumps(provenance, indent=2) + "\n")
    license_text = subprocess.check_output(["git", "-C", str(SOURCE), "show", f'{PINS["core"]}:LICENSE.txt'], text=True)
    install("participant/workspace/TBMODELS_LICENSE.txt", license_text)


if __name__ == "__main__":
    main()

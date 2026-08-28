"""Check internal identities only; this contains no expected answer."""

import argparse
import json
from pathlib import Path

import numpy as np


def check(case, output):
    spec = json.loads((case / "case.json").read_text())
    errors = {}
    with np.load(output, allow_pickle=False) as arrays:
        for prefix, track in (("import", "import"), ("map", "mapping")):
            positions = arrays[f"{prefix}_pos"]
            matrix_one = arrays[f"{prefix}_h1"]
            matrix_two = arrays[f"{prefix}_h2"]
            phases = np.exp(2j * np.pi * np.asarray(spec[track]["kpoints"]) @ positions.T)
            converted = phases.conj()[:, :, None] * matrix_two * phases[:, None, :]
            errors[f"{prefix}_conventions"] = float(np.max(np.abs(converted - matrix_one)))
            errors[f"{prefix}_hermiticity"] = float(np.max(np.abs(matrix_two - matrix_two.conj().transpose(0, 2, 1))))
            errors[f"{prefix}_bands"] = float(np.max(np.abs(np.linalg.eigvalsh(matrix_two) - arrays[f"{prefix}_bands"])))
    print(json.dumps(errors, indent=2))
    if not all(np.isfinite(value) and value < 1e-8 for value in errors.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    check(arguments.input, arguments.output)

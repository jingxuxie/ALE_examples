"""Cross-check selected spectra with the later official Rust implementation."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
RUNTIME = CONCEPT.parents[1] / "author/runtime4"
sys.path.insert(0, str(RUNTIME))
sys.dont_write_bytecode = True

import numpy as np
import phonopy
import phonors
from phonopy.phonon.grid import BZGrid
from phonopy.phonon.tetrahedron_method import get_integration_weights


def main():
    assert phonopy.__version__ == "4.1.0"
    private = CONCEPT / "private"
    cases = json.loads((private / "challenge_pool/manifest.json").read_text())
    selected = [case for case in cases if case["id"] in
                ("pool_skew_17029", "heldout_ties_79043", "heldout_flat_79043")]
    report = {"phonopy": phonopy.__version__, "backend": "Rust", "cases": [],
              "module_sha256": {name: hashlib.sha256((RUNTIME / name).read_bytes()).hexdigest()
                                for name in ("phonopy/phonon/grid.py", "phonopy/phonon/tetrahedron_method.py")}}
    for case in selected:
        with np.load(private / case["input"], allow_pickle=False) as data, \
             np.load(private / case["reference"], allow_pickle=False) as reference:
            grid = BZGrid(data["grid_matrix"], reciprocal_lattice=data["reciprocal_lattice"],
                          transformation_matrix=np.eye(3), is_time_reversal=False)
            addresses = data["grid_addresses"] @ grid.P.T % grid.D_diag
            indices = addresses[:, 0] + grid.D_diag[0] * (addresses[:, 1] + grid.D_diag[1] * addresses[:, 2])
            values = np.empty_like(data["frequencies"], order="C")
            values[indices] = data["frequencies"]
            result = {"id": case["id"]}
            for field, function in (("dos", "I"), ("cumulative", "J")):
                total = np.zeros_like(reference[field])
                for start in range(0, len(values), 512):
                    weights = get_integration_weights(data["sampling_points"], values, grid,
                        grid_points=grid.grg2bzg[start : start + 512],
                        bzgp2irgp_map=grid.bzg2grg, function=function, lang="Rust")
                    total += weights.sum(axis=0)
                total /= len(values)
                np.testing.assert_allclose(total, reference[field], rtol=2e-8, atol=2e-10)
                result[field + "_maximum_difference"] = float(np.max(np.abs(total - reference[field])))
            report["cases"].append(result)
            print(json.dumps(result), flush=True)
    assert len(selected) == 3
    report["passed"] = True
    (HERE / "runtime4_validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

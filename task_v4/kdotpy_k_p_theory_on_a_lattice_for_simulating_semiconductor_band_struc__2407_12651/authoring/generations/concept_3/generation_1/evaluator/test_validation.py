import copy
import json
import os
from pathlib import Path
import sys
import unittest

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import baseline, components, pack, unpack
from evaluate import load_witness, validate_witness, verify_freeze
from reference import PAULI_X, PAULI_Y, PAULI_Z, IDENTITY, fourier_hoppings, matrix_values, topology_certificate

CONFIG = json.loads((ROOT / "participant/input/model.json").read_text())


class Validation(unittest.TestCase):
    def test_frozen_contract(self):
        self.assertTrue(verify_freeze()["freeze_id"])

    def test_independent_fourier_assembly_all_channels(self):
        generator = np.random.default_rng(912)
        horizontal, vertical = generator.uniform(-np.pi, np.pi, (2, 27))
        for index in range(30):
            parameters = pack(baseline())
            parameters[index] += 0.137
            witness = unpack(parameters)
            values = components(witness, horizontal, vertical)
            expected = sum(values[:, index, None, None] * matrix for index, matrix in enumerate((IDENTITY, PAULI_X, PAULI_Y, PAULI_Z)))
            actual = matrix_values(fourier_hoppings(witness), horizontal, vertical)
            np.testing.assert_allclose(actual, expected, atol=3e-14)
            radius = np.linalg.norm(values[:, 1:], axis=-1)
            np.testing.assert_allclose(np.linalg.eigvalsh(actual), np.stack((values[:, 0] - radius, values[:, 0] + radius), axis=-1), atol=3e-14)

    def test_negative_json_controls(self):
        cases = {}
        candidate = baseline()
        candidate["mass"] = True
        cases["boolean"] = json.dumps(candidate)
        candidate = baseline()
        candidate["spin_orbit"] = [0.001] * 11
        cases["support"] = json.dumps(candidate)
        candidate = baseline()
        candidate["scalar"][0] = 0.75001
        cases["bound"] = json.dumps(candidate)
        cases["nan"] = json.dumps(baseline()).replace('"mass": -1.0', '"mass": NaN')
        cases["duplicate"] = json.dumps(baseline())[:-1] + ',"mass":-1.0}'
        cases["oversized"] = ' ' * 32769
        candidate = baseline()
        candidate["execute"] = "__import__('os').system('false')"
        cases["code_as_data"] = json.dumps(candidate)
        for name, payload in cases.items():
            path = ROOT / "adversary" / (name + ".json")
            path.write_text(payload)
            with self.subTest(name=name), self.assertRaises(ValueError):
                load_witness(path, CONFIG)

    def test_topology_gauge_and_trivial_control(self):
        first = topology_certificate(baseline(), 128)
        second = topology_certificate(baseline(), 128, (0.37, 0.19), 71)
        self.assertTrue(first["certified"] and second["certified"])
        self.assertEqual(first["chern"], -1)
        self.assertEqual(second["chern"], -1)
        candidate = baseline()
        candidate["orbital_mass"] = [0.0] * 9
        candidate["mass"] = -1.9
        self.assertEqual(topology_certificate(candidate, 128)["chern"], 0)
        (ROOT / "adversary/trivial.json").write_text(json.dumps(candidate))

    def test_gap_closure_and_indirect_gap_control(self):
        candidate = baseline()
        candidate["orbital_mass"][0] = 0.5
        self.assertFalse(topology_certificate(candidate, 128)["certified"])
        (ROOT / "adversary/gap_closed.json").write_text(json.dumps(candidate))
        candidate = baseline()
        candidate["scalar"][:3] = [0.75, 0.75, 0.75]
        axis = np.arange(64) * 2.0 * np.pi / 64
        horizontal, vertical = np.meshgrid(axis, axis, indexing="ij")
        spectra = np.linalg.eigvalsh(matrix_values(fourier_hoppings(candidate), horizontal, vertical))
        self.assertGreater(float(np.min(spectra[..., 1] - spectra[..., 0])), 1.99)
        self.assertLess(float(np.min(spectra[..., 1]) - np.max(spectra[..., 0])), 0.0)
        (ROOT / "adversary/indirect_overlap.json").write_text(json.dumps(candidate))


if __name__ == "__main__":
    unittest.main(verbosity=2)

import copy
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

from evaluate import ROOT, HIDDEN, aggregate, invalid_case, load_references, score_field
from independent import checked_field, energy_gradient, read_case


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target = read_case(HIDDEN / "target.json")
        cls.case = read_case(ROOT / "participant/input/cases/dev_pinning.json")
        cls.field = checked_field(ROOT / "attempts/baseline/dev_pinning.npz", cls.case)
        cls.energy = energy_gradient(cls.case, cls.field)[0]
        cls.reference = {"case_id": "test", "family": "strong_pinning", "baseline_energy": cls.energy + 10, "witness_energy": cls.energy - 10}

    def test_energy_is_recomputed(self):
        record = score_field(self.reference, self.case, self.field, 30, self.target)
        self.assertTrue(record["valid"])
        self.assertAlmostEqual(record["checked_energy"], self.energy, places=12)
        self.assertAlmostEqual(record["case_score"], 0.5)
        self.assertAlmostEqual(record["runtime_score"], 0.5)

    def test_witness_saturation_not_ground_state(self):
        reference = dict(self.reference, baseline_energy=self.energy + 20, witness_energy=self.energy + 10)
        record = score_field(reference, self.case, self.field, 1, self.target)
        self.assertEqual(record["raw_gap_closure"], 2)
        self.assertEqual(record["case_score"], 1)
        self.assertTrue(record["valid"])

    def test_regression_fails_despite_other_scores(self):
        reference = dict(self.reference, baseline_energy=self.energy - 1, witness_energy=self.energy - 2)
        record = score_field(reference, self.case, self.field, 1, self.target)
        self.assertFalse(record["valid"])
        self.assertEqual(record["case_score"], 0)
        self.assertIn("regression", record["reason"])

    def test_stationarity_and_deadline(self):
        field = self.field * 0.9
        record = score_field(self.reference, self.case, field, 1, self.target)
        self.assertFalse(record["valid"])
        self.assertIn("gradient", record["reason"])
        record = score_field(self.reference, self.case, self.field, 60.001, self.target)
        self.assertFalse(record["valid"])
        self.assertIn("deadline", record["reason"])
        self.assertEqual(record["runtime_score"], 0)

    def records(self, family_values):
        records = []
        for family, value in zip(self.target["families"], family_values):
            for number in range(2):
                records.append({"case_id": family + str(number), "family": family, "case_score": value, "runtime_score": 0.3, "valid": True, "reason": "ok"})
        return records

    def test_family_balancing_and_worst_family_gate(self):
        report = aggregate(self.records([1, 1, 0.44]), self.target)
        self.assertAlmostEqual(report["core_score"], 2.44 / 3)
        self.assertFalse(report["passed"])
        self.assertEqual(report["worst_family"], "high_vortex")
        report = aggregate(self.records([0.65, 0.65, 0.65]), self.target)
        self.assertTrue(report["passed"])
        self.assertAlmostEqual(report["runtime_score"], 0.3)

    def test_invalid_cases_cannot_be_dropped(self):
        records = self.records([1, 1, 1])
        records[-1] = invalid_case(records[-1], "bad NPZ")
        report = aggregate(records, self.target)
        self.assertFalse(report["passed"])
        self.assertAlmostEqual(report["core_score"], 5 / 6)
        with self.assertRaises(ValueError):
            aggregate(records[:-1], self.target)
        records[-1] = records[-2]
        with self.assertRaises(ValueError):
            aggregate(records, self.target)

    def test_zip_bombs_and_forged_metadata(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "attempts") as directory:
            path = Path(directory) / "result.npz"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("psi.npy", b"0" * (4194304 + 1))
            self.assertLess(path.stat().st_size, 4194304)
            with self.assertRaises(ValueError):
                checked_field(path, self.case)
            np.savez(path, psi=self.field, energy=self.energy - 1000, runtime=0)
            with self.assertRaises(ValueError):
                checked_field(path, self.case)
            header = repr({"descr": "<c16", "fortran_order": False, "shape": (10**12, 10**12)}).encode("ascii")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("psi.npy", b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header)
            with self.assertRaises(ValueError):
                checked_field(path, self.case)

    def test_frozen_references(self):
        if not (HIDDEN / "manifest.json").exists():
            self.skipTest("manifest not frozen yet")
        target, records = load_references()
        self.assertEqual(len(records), 6)
        self.assertEqual(target["core_min"], 0.65)
        for record in records:
            self.assertGreaterEqual(record["baseline_energy"] - record["witness_energy"], 0.5)
        with patch("evaluate.digest", return_value="corrupted"):
            with self.assertRaises(ValueError):
                load_references()


if __name__ == "__main__":
    unittest.main(verbosity=2)

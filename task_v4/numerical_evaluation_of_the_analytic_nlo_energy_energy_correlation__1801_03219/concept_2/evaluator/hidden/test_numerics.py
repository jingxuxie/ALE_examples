"""Author-side checks of rules, source precision, and witness validation."""

import json
import math
import sys
import unittest
from pathlib import Path

import mpmath as mp
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))
from native_kernel import _components
from problem import Kernel, validate
from target import GWEIGHTS, KWEIGHTS, NODES, integrate, panel


class NumericalTests(unittest.TestCase):
    def test_gauss_and_kronrod_polynomial_exactness(self):
        for degree in range(32):
            expected = 0.0 if degree % 2 else 2 / (degree + 1)
            self.assertAlmostEqual(math.fsum(KWEIGHTS * NODES**degree), expected, delta=2e-15)
            if degree <= 19:
                self.assertAlmostEqual(math.fsum(GWEIGHTS * NODES**degree), expected, delta=2e-15)

    def test_adaptive_regular_and_oscillatory_functions(self):
        cases = [(np.exp, math.e - 1), (lambda points: np.sin(197 * points), (1 - math.cos(197)) / 197),
                 (lambda points: 1 / (.03 + points), math.log(1.03 / .03))]
        for function, expected in cases:
            result = integrate(function)
            self.assertTrue(result["converged"])
            self.assertGreaterEqual(result["evaluations"], 252)
            self.assertLess(abs(result["value"] - expected), 2e-10)
            self.assertGreater(result["estimated_error"], 0)

    def test_kernel_against_native_precision(self):
        kernel = Kernel()
        for point in (".02", ".071", ".317", ".701", ".98"):
            references = []
            for precision in (55, 85):
                with mp.workdps(precision):
                    argument = mp.mpf(point)
                    references.append([4 * argument * (1 - argument) * component for component in _components(argument)])
            with mp.workdps(85):
                self.assertLess(max(abs(first - second) for first, second in zip(*references)), mp.mpf("1e-38"))
            values = kernel(np.array([float(point)]))[0]
            self.assertLess(max(abs(value - float(reference)) for value, reference in zip(values, references[1])), 2e-11)

    def test_schema_rejects_nonfinite_boolean_and_extra_fields(self):
        witness = {"version": 1, "bin": "central", "band_start": 1, "tilt": 0, "curvature": 0,
                   "cosine": [10**10] + [0] * 11, "sine": [0] * 12}
        validate(witness)
        for key, value in (("version", True), ("tilt", float("nan")), ("band_start", 54), ("bin", "endpoint")):
            broken = dict(witness)
            broken[key] = value
            with self.assertRaises(ValueError):
                validate(broken)
        broken = dict(witness, answer=0)
        with self.assertRaises(ValueError):
            validate(broken)


if __name__ == "__main__":
    unittest.main(verbosity=2)

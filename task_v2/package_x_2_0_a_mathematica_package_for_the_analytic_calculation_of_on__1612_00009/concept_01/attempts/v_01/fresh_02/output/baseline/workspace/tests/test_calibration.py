import math
import unittest

from loopaudit.backend import evaluate
from loopaudit.contract import decode


class Calibration(unittest.TestCase):
    def settings(self):
        import json
        from pathlib import Path
        return json.loads((Path(__file__).resolve().parents[1] / "profiles.json").read_text())["production"]

    def test_zero_momentum_equal_mass_box(self):
        request = {"id": "calibration_box", "masses2": [1] * 4, "invariants": [[0] * 4 for index in range(4)]}
        values = decode(evaluate(request, self.settings())["coefficients"]["base"])
        self.assertLess(max(abs(values[:3])), 1e-8)
        self.assertLess(abs(values[3] - 1 / 6), 1e-8)

    def test_tadpole(self):
        request = {"id": "calibration_tadpole", "masses2": [2], "invariants": [[0]], "mu2": 1}
        values = decode(evaluate(request, self.settings())["coefficients"]["base"])
        self.assertLess(abs(values[0] - 2), 1e-8)
        self.assertLess(abs(values[3] - 2 * (1 - math.log(2))), 1e-8)


if __name__ == "__main__":
    unittest.main()

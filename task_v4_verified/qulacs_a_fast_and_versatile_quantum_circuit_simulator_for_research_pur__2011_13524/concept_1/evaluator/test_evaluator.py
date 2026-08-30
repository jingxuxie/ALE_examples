import copy
import importlib.util
import json
from pathlib import Path
import random
import unittest

from evaluate import independent_check


ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
        cls.model = module("public_cost", ROOT / "participant/workspace/model.py")
        cls.baseline = module("baseline", ROOT / "participant/baseline/solution.py")

    def test_independent_cost_agrees(self):
        for entry in self.entries:
            case = entry["case"]
            blocks = entry["baseline_schedule"]
            self.assertAlmostEqual(independent_check(case, blocks), self.model.validate_and_cost(case, blocks), places=8)
            self.assertAlmostEqual(independent_check(case, blocks), entry["baseline_cost"], places=8)

    def test_random_valid_baseline_orders(self):
        rng = random.Random(9)
        for entry in self.entries[:8]:
            case = entry["case"]
            order = self.baseline.reordered(case, rng.choice([1, 2, 4]), rng.choice(["dense", "diagonal"]))
            blocks = [[index] for index in order]
            self.assertGreater(independent_check(case, blocks), 0)

    def test_malformed_rejected(self):
        case = self.entries[0]["case"]
        valid = [[index] for index in range(len(case["gates"]))]
        mutations = [[], valid[:-1], valid + [[0]], [[True]] + valid[1:], [[-1]] + valid[1:], [[float("nan")]] + valid[1:]]
        for schedule in mutations:
            with self.assertRaises(ValueError):
                independent_check(case, schedule)

    def test_dependency_rejected(self):
        case = self.entries[0]["case"]
        schedule = [[index] for index in range(len(case["gates"]))]
        first = 0
        second = next(index for index in range(1, len(case["gates"])) if set(case["gates"][first]["qubits"]) & set(case["gates"][index]["qubits"]))
        schedule[first], schedule[second] = schedule[second], schedule[first]
        with self.assertRaises(ValueError):
            independent_check(case, schedule)

    def test_barriers_rejected(self):
        entry = next(entry for entry in self.entries if entry["case"]["gates"][-1]["epoch"] > 0)
        case = entry["case"]
        boundary = next(index for index, gate in enumerate(case["gates"]) if gate["epoch"] > 0)
        blocks = [[index] for index in range(len(case["gates"]))]
        blocks[boundary - 1:boundary + 1] = [[boundary - 1, boundary]]
        with self.assertRaises(ValueError):
            independent_check(case, blocks)


if __name__ == "__main__":
    unittest.main()

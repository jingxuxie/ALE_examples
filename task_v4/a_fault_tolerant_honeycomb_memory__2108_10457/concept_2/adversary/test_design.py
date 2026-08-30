import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from design_common import aggregate, ambiguity, generate_supports, load_case, read_design, score_case
from evaluate import evaluate


def independent_rank(vectors):
    vectors = list(vectors)
    rank = 0
    for bit in range(max((vector.bit_length() for vector in vectors), default=0)):
        pivot = next((index for index in range(rank, len(vectors)) if vectors[index] & (1 << bit)), None)
        if pivot is None:
            continue
        vectors[rank], vectors[pivot] = vectors[pivot], vectors[rank]
        for index in range(rank + 1, len(vectors)):
            if vectors[index] & (1 << bit):
                vectors[index] ^= vectors[rank]
        rank += 1
    return rank


class DesignTests(unittest.TestCase):
    def test_rank_matches_independent_elimination_and_exhaustion(self):
        generator = random.Random(86524)
        for _ in range(300):
            vectors = [generator.randrange(1 << 10) for _ in range(generator.randrange(10))]
            expected = independent_rank(vectors) - independent_rank([vector >> 4 for vector in vectors])
            self.assertEqual(ambiguity(vectors), expected)
            combinations = {0}
            for vector in vectors:
                combinations |= {value ^ vector for value in list(combinations)}
            invisible_logicals = {value for value in combinations if value < 16}
            self.assertEqual(len(invisible_logicals), 1 << expected)
            self.assertEqual(bool(ambiguity(vectors, True)), bool(expected))

    def test_empty_benign_and_all_four_logicals(self):
        self.assertEqual(ambiguity([]), 0)
        self.assertEqual(ambiguity([16, 16]), 0)
        self.assertEqual(ambiguity([16, 17]), 1)
        self.assertEqual(ambiguity([1, 2, 4, 8]), 4)

    def test_invalid_artifacts(self):
        invalid = [[], {}, {"z_image": [2] * 23}, {"z_image": [2] * 25}, {"z_image": [True] * 24}, {"z_image": [2.0] * 24}, {"z_image": [3] * 24}, {"z_image": ["Z"] * 24}, {"z_image": [2] * 24, "detectors": []}]
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            artifact = Path(directory) / "design.json"
            for value in invalid:
                artifact.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    read_design(artifact)
            artifact.write_text('{"z_image": [], "z_image": ' + json.dumps([2] * 24) + '}')
            with self.assertRaises(ValueError):
                read_design(artifact)

    def test_nofollow_special_files_and_uniform_failures(self):
        required = {"core_score", "worst_family_score", "runtime_score", "resource_score", "runtime_seconds", "valid", "passed", "reason"}
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            directory = Path(directory)
            link = directory / "link.json"
            link.symlink_to(ROOT / "participant" / "baseline" / "design.json")
            fifo = directory / "pipe.json"
            os.mkfifo(fifo)
            deep = directory / "deep.json"
            deep.write_text("[" * 2000 + "]" * 2000)
            for artifact in (link, fifo, directory, deep, Path("/dev/null")):
                result = evaluate(artifact)
                self.assertFalse(result["valid"])
                self.assertFalse(result["passed"])
                self.assertTrue(required <= set(result))
                self.assertEqual(result["core_score"], 0)
                self.assertLess(result["runtime_seconds"], 2)

    def test_trusted_hash_mismatch_fails_closed(self):
        with mock.patch("evaluate.hashlib.sha256") as digest:
            digest.return_value.hexdigest.return_value = "not_the_expected_hash"
            result = evaluate(ROOT / "participant" / "baseline" / "design.json")
        self.assertFalse(result["valid"])
        self.assertFalse(result["passed"])
        self.assertIn("hash mismatch", result["reason"])

    def test_oversized_artifact(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            artifact = Path(directory) / "oversized.json"
            artifact.write_text(" " * 16385)
            with self.assertRaises(ValueError):
                read_design(artifact)

    def test_public_and_hidden_math_identical(self):
        self.assertEqual((ROOT / "evaluator" / "design_common.py").read_bytes(), (ROOT / "participant" / "workspace" / "design_common.py").read_bytes())
        for scale in (1, 2, 3):
            name = f"scale_{scale}.json.gz"
            self.assertEqual((ROOT / "evaluator" / "hidden" / name).read_bytes(), (ROOT / "participant" / "input" / name).read_bytes())

    def test_supports_valid_and_not_practice(self):
        hidden = json.loads((ROOT / "evaluator" / "hidden" / "supports.json").read_text())
        public = json.loads((ROOT / "participant" / "input" / "practice.json").read_text())
        for identifier, records in hidden.items():
            case = load_case(ROOT / "evaluator" / "hidden" / (identifier + ".json.gz"))
            for record in records:
                support = record["support"]
                self.assertEqual(support, sorted(set(support)))
                self.assertTrue(all(0 <= index < len(case["columns"]) for index in support))
            self.assertFalse({(record["family"], tuple(record["support"])) for record in records} & {(record["family"], tuple(record["support"])) for record in public[identifier]})
            for triple in case["columns"]:
                self.assertEqual(triple[0] ^ triple[1] ^ triple[2], 0)

    def test_baseline_generator_and_fixed_protocol(self):
        output = subprocess.check_output([sys.executable, str(ROOT / "participant" / "baseline" / "solve.py")], text=True)
        self.assertEqual(json.loads(output), json.loads((ROOT / "participant" / "baseline" / "design.json").read_text()))
        baseline = evaluate(ROOT / "participant" / "baseline" / "design.json")
        self.assertFalse(baseline["passed"])
        self.assertTrue(baseline["valid"])
        self.assertEqual(baseline["core_score"], baseline["correctness_fraction"])
        self.assertEqual(baseline["worst_family_score"], baseline["worst_group_fraction"])
        self.assertEqual(baseline["resource_score"], 1)
        protocol = json.loads((ROOT / "evaluator/protocol.json").read_text())
        self.assertEqual(protocol["target_fraction"], 0.85)
        self.assertTrue(all(floor == 0.60 for floor in protocol["group_floors"].values()))
        if protocol.get("generation", 1) == 1:
            champion = evaluate(ROOT / "champions/generator_only.json")
            self.assertTrue(champion["passed"])
            self.assertGreater(champion["correctness_fraction"] - baseline["correctness_fraction"], 0.50)
        else:
            self.assertEqual(read_design(ROOT / "participant/baseline/design.json"),
                             read_design(ROOT / "champions/generation_1/design.json"))
            self.assertEqual(protocol["supports_per_group"], 4096)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DesignTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful(), "fresh_agents_run_by_this_validation": 0,
              "generation": json.loads((ROOT / "evaluator/protocol.json").read_text()).get("generation", 1)}
    (ROOT / "adversary" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)

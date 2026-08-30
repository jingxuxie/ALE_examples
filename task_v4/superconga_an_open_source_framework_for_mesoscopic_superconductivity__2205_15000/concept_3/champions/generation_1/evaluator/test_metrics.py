import copy
import unittest

import evaluate


class MetricTests(unittest.TestCase):
    def test_exact_and_permuted(self):
        scene = evaluate.model.draw_scene(6, "dispersed")
        estimate = copy.deepcopy(scene)
        estimate["impurities"].reverse()
        estimate["vortices"].reverse()
        metrics = evaluate.score_scene(scene, estimate)
        self.assertEqual(metrics["joint_success"], 1)
        self.assertAlmostEqual(metrics["quality"], 1)

    def test_missing_support_and_wrong_strength_penalized(self):
        scene = evaluate.model.draw_scene(6, "dispersed")
        estimate = copy.deepcopy(scene)
        estimate["impurities"][0]["strength"] *= -1
        self.assertEqual(evaluate.score_scene(scene, estimate)["joint_success"], 0)
        occupied = {item["site"] for item in estimate["impurities"]}
        estimate["impurities"][0]["site"] = next(site for site in evaluate.model.SPEC["impurity_sites"] if site not in occupied)
        metrics = evaluate.score_scene(scene, estimate)
        self.assertLess(metrics["support_f1"], 1)
        self.assertGreater(metrics["relative_strength_error"], 0.2)

    def test_worst_family_is_independent_gate(self):
        results = []
        for family in evaluate.model.SPEC["families"]:
            for index in range(4):
                good = family != "clustered" or index == 0
                metrics = {"joint_success": int(good), "support_f1": 1.0, "relative_strength_error": 0.0,
                           "vortex_exact": 1, "vortex_count_exact": 1, "quality": 1.0}
                results.append({"family": family, "metrics": metrics, "protocol_valid": True, "wall_seconds": 1.0})
        summary = evaluate.aggregate(results, official=True)
        self.assertTrue(summary["checks"]["core"])
        self.assertFalse(summary["checks"]["worst_family"])
        self.assertFalse(summary["passed"])
        results[-1]["protocol_valid"] = False
        self.assertFalse(evaluate.aggregate(results)["checks"]["protocol"])

    def test_partial_or_calibration_never_official_pass(self):
        scene = evaluate.model.draw_scene(6, "dispersed")
        results = [{"family": family, "metrics": evaluate.score_scene(scene, scene), "protocol_valid": True,
                    "wall_seconds": 1.0} for family in evaluate.model.SPEC["families"] for _ in range(4)]
        self.assertTrue(evaluate.aggregate(results, official=True)["passed"])
        self.assertFalse(evaluate.aggregate(results, official=False)["passed"])
        self.assertFalse(evaluate.aggregate(results[:-1], official=True)["passed"])

    def test_strict_json(self):
        for text in ('{"type":"query","type":"final"}', '{"value":NaN}', '[]', '{"value":Infinity}'):
            with self.assertRaises(evaluate.ProtocolError):
                evaluate.strict_json(text)

    def test_metadata_is_public_only(self):
        self.assertEqual(set(evaluate.metadata()), {"type", "protocol", "model", "target"})
        self.assertEqual(evaluate.metadata()["model"], evaluate.model.SPEC)
        self.assertNotIn("seed", evaluate.metadata())
        self.assertNotIn("scene", evaluate.metadata())


if __name__ == "__main__":
    unittest.main()
